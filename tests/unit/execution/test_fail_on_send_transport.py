"""Behavioral tests for the interim fail-on-send connector transport (W1).

Owner decision 2026-10-06 (SPEC.md section 11 connector inventory): until a real
connector is named, the worker runs with a transport that refuses to send. It
lets the worker start and resume durable workflows while nothing leaves the box;
a step that would send raises loudly and its run stays persisted for a later
retry with a real connector. This is reversible: swap the transport, no caller
changes.

SPEC.md section 6 calls connectors "outbound adapters with explicit scopes and
replay safe operations"; SPEC.md section 9 keeps a client's resource tenant
scoped. The transport is the raw vendor seam, so a refusal must be a named error
rather than a silent no-op that would record a false success.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.execution.domain.connector import ConnectorEffect
from redops.contexts.execution.domain.errors import ConnectorSendRefusedError
from redops.contexts.execution.infrastructure.connectors import (
    FailOnSendConnectorTransport,
    IdempotentConnector,
    InMemoryExternalOperationStore,
)

TENANT = "3fmindset"
ON = date(2026, 10, 6)


def effect() -> ConnectorEffect:
    return ConnectorEffect(
        tenant_id=TENANT,
        idempotency_key="run-1:publish-asset",
        connector="redop",
        target="publish-asset",
        payload_digest="sha256:abc",
        requested_on=ON,
    )


class FailOnSendTransportTests(unittest.TestCase):
    def test_send_refuses_loudly_with_a_named_error(self) -> None:
        transport = FailOnSendConnectorTransport()

        with self.assertRaises(ConnectorSendRefusedError):
            transport.send(effect())

    def test_a_refused_send_records_no_external_operation(self) -> None:
        # The refusal must happen before the store records anything, so a
        # durable worker cannot mistake a refused send for a delivered effect.
        store = InMemoryExternalOperationStore()
        connector = IdempotentConnector(
            store=store, transport=FailOnSendConnectorTransport()
        )

        with self.assertRaises(ConnectorSendRefusedError):
            connector.deliver(effect())

        self.assertIsNone(store.get(TENANT, "run-1:publish-asset"))


if __name__ == "__main__":
    unittest.main()
