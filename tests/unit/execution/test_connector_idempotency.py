"""Behavioral tests for the idempotency-keyed Execution connector seam.

SPEC.md section 11 requires "duplicate delivery creates one external operation",
SPEC.md section 6 calls connectors "outbound adapters with explicit scopes and
replay safe operations", and SPEC.md section 7 requires an idempotency key on
every mutation where a retry matters. SPEC.md section 9 keeps a client's
resource tenant scoped.

These tests exercise the ``ConnectorPort`` seam through its reference adapter:
the same effect delivered twice runs the underlying transport once and both
deliveries resolve to the one recorded external operation; a reused key with
different content is refused rather than silently sent a second time; and the
key is scoped per client, so one client's key never resolves another's
operation.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.execution.domain.connector import (
    ConnectorEffect,
    ExternalOperation,
)
from redops.contexts.execution.domain.errors import (
    ConnectorIdempotencyConflictError,
    ConnectorTenantBoundaryError,
    InvalidConnectorEffectError,
)
from redops.contexts.execution.infrastructure.connectors import (
    IdempotentConnector,
    InMemoryExternalOperationStore,
    RecordingConnectorTransport,
)

TENANT = "3fmindset"
OTHER_TENANT = "client-other"
ON = date(2026, 10, 3)


def effect(
    *,
    tenant_id: str = TENANT,
    idempotency_key: str = "delivery-1",
    connector: str = "crm",
    target: str = "lead:123",
    payload_digest: str = "sha256:abc",
) -> ConnectorEffect:
    return ConnectorEffect(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        connector=connector,
        target=target,
        payload_digest=payload_digest,
        requested_on=ON,
    )


class ConnectorEffectTests(unittest.TestCase):
    def test_a_blank_idempotency_key_is_refused(self):
        with self.assertRaises(InvalidConnectorEffectError):
            effect(idempotency_key="   ")

    def test_a_blank_connector_is_refused(self):
        with self.assertRaises(InvalidConnectorEffectError):
            effect(connector="")

    def test_an_operation_is_one_exact_effect(self):
        operation = ExternalOperation(
            effect=effect(), external_ref="crm-op-1", delivered_on=ON
        )

        self.assertTrue(operation.matches(effect()))
        self.assertFalse(operation.matches(effect(payload_digest="sha256:def")))

    def test_a_blank_external_ref_is_refused(self):
        with self.assertRaises(InvalidConnectorEffectError):
            ExternalOperation(effect=effect(), external_ref="", delivered_on=ON)


class IdempotentConnectorTests(unittest.TestCase):
    def setUp(self):
        self.transport = RecordingConnectorTransport()
        self.store = InMemoryExternalOperationStore()
        self.connector = IdempotentConnector(
            store=self.store, transport=self.transport
        )

    def test_a_first_delivery_sends_once_and_records_one_operation(self):
        operation = self.connector.deliver(effect())

        self.assertEqual(1, len(self.transport.sent))
        self.assertEqual("crm-op-1", operation.external_ref)
        self.assertEqual(operation, self.store.get(TENANT, "delivery-1"))

    def test_duplicate_delivery_creates_one_external_operation(self):
        first = self.connector.deliver(effect())
        second = self.connector.deliver(effect())

        self.assertEqual(1, len(self.transport.sent))
        self.assertEqual(first, second)
        self.assertEqual("crm-op-1", second.external_ref)

    def test_a_reused_key_with_different_content_is_refused(self):
        self.connector.deliver(effect())

        with self.assertRaises(ConnectorIdempotencyConflictError):
            self.connector.deliver(effect(payload_digest="sha256:changed"))

        self.assertEqual(1, len(self.transport.sent))

    def test_a_reused_key_for_another_connector_is_refused(self):
        self.connector.deliver(effect(connector="crm"))

        with self.assertRaises(ConnectorIdempotencyConflictError):
            self.connector.deliver(effect(connector="email"))

    def test_the_key_is_scoped_per_client(self):
        self.connector.deliver(effect(tenant_id=TENANT))
        other = self.connector.deliver(effect(tenant_id=OTHER_TENANT))

        self.assertEqual(2, len(self.transport.sent))
        self.assertEqual("crm-op-2", other.external_ref)
        self.assertNotEqual(
            self.store.get(TENANT, "delivery-1"),
            self.store.get(OTHER_TENANT, "delivery-1"),
        )

    def test_a_blank_tenant_is_refused(self):
        with self.assertRaises(ConnectorTenantBoundaryError):
            self.connector.deliver(effect(tenant_id="   "))


if __name__ == "__main__":
    unittest.main()
