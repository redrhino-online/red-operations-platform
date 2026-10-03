"""Adapter contract tests for the PostgreSQL ``GateLedgerRepository``.

ADR 0003 makes RED's gate ledger durable in PostgreSQL, and SPEC.md section 6
says infrastructure adapters implement ports. These tests exercise the real
``PostgresGateLedgerRepository`` against the local compose database: the schema
is created by the committed migration ``0001_gate_decisions`` (SPEC.md section
6: migrations committed with schema changes), and a decision recorded through
the shared stage 0 use case is persisted and reloaded as an aggregate with its
exact pinned asset versions, its tenant and its append-only history (SPEC.md
sections 3 and 4).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter (Python 3.10, no third-party
packages) still runs the rest of the suite. Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/governance/test_gate_ledger_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from redops.contexts.engagement.application.commands import (
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageZeroGateHandler,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import (
    CANONICAL_INTAKE_KINDS,
    ClientAuthority,
    IntakeAsset,
    IntakePackage,
)
from redops.contexts.governance.domain.errors import (
    AssetPackageMismatchError,
    CrossTenantGateError,
)
from redops.contexts.governance.domain.templates import (
    stage_zero_to_ten_template,
)
from redops.contexts.governance.domain.value_objects import GateDisposition
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)

ON = date(2026, 10, 2)
DUE = date(2026, 10, 16)
TENANT = "client-3f"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE = "stage-1-diagnosis"
CORRELATION = "corr-stage-0"


def workspace() -> ClientWorkspace:
    return ClientWorkspace(
        workspace_id="ws-3f",
        tenant_id=TENANT,
        authorities=(
            ClientAuthority(actor=OWNER, authority="production-owner"),
            ClientAuthority(
                actor=APPROVER, authority="client-designated-authority"
            ),
        ),
    )


def sourced_claim() -> Claim:
    return Claim(
        claim_id="claim-intake-1",
        tenant_id=TENANT,
        statement="Intake fact recorded with the client",
        provenance=ProvenanceClass.KNOWN,
        citations=(
            frozenset({SourceCitation("source-intake", "sha256:abc", "p.1")}),
        ),
        confidence_note="captured during intake",
    )


def intake_package() -> IntakePackage:
    assets = tuple(
        IntakeAsset(
            asset_id=f"{kind.value}-3f@1",
            tenant_id=TENANT,
            kind=kind,
            version=1,
            owner=OWNER,
            summary=f"Recorded {kind.value}",
            evidence_claim_ids=("claim-intake-1",),
        )
        for kind in CANONICAL_INTAKE_KINDS
    )
    return IntakePackage(
        package_id="intake-3f", tenant_id=TENANT, assets=assets
    )


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresGateLedgerRepositoryTests(unittest.TestCase):
    """The port contract, exercised against the real PostgreSQL schema."""

    @classmethod
    def setUpClass(cls) -> None:
        from alembic import command
        from alembic.config import Config

        cls._psycopg = importlib.import_module("psycopg")
        cls._jsonb = importlib.import_module("psycopg.types.json").Jsonb
        config = Config(str(REPO_ROOT / "alembic.ini"))
        config.set_main_option(
            "script_location",
            str(
                REPO_ROOT
                / "backend/redops/shared/persistence/migrations"
            ),
        )
        config.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(config, "head")
        cls._connection = cls._psycopg.connect(DATABASE_URL)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._connection.close()

    def setUp(self) -> None:
        from redops.contexts.governance.infrastructure.repositories import (
            PostgresGateLedgerRepository,
        )

        self.template = stage_zero_to_ten_template()
        self.repository = PostgresGateLedgerRepository(self._connection)
        self.handler = RecordStageZeroGateHandler()
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE gate_decisions RESTART IDENTITY")
        self._connection.commit()

    def record_stage_zero(self):
        from redops.contexts.governance.domain.entities import StageRun

        run = StageRun(
            engagement="ws-3f",
            stage_number=0,
            template_version=self.template.version,
            assigned_owner=OWNER,
        )
        run.start(
            actor=OWNER,
            reason="intake work began",
            on=ON,
            correlation_id=CORRELATION,
        )
        command = RecordStageZeroGateCommand(
            template=self.template,
            workspace=workspace(),
            package=intake_package(),
            claims=(sourced_claim(),),
            stage_run=run,
            approver=APPROVER,
            proposed_by=OWNER,
            scope=SCOPE,
            checkpoint_evidence="all twelve stage 0 assets reviewed",
            rationale="intake complete and owned",
            assigned_owner=OWNER,
            due_on=DUE,
            on=ON,
            correlation_id=CORRELATION,
        )
        decision = self.handler.handle(
            command, ledger=self.repository.load(self.template, TENANT)
        )
        self.repository.append(decision)
        return decision

    def test_a_fresh_repository_loads_an_empty_ledger(self) -> None:
        ledger = self.repository.load(self.template, TENANT)

        self.assertIsNone(ledger.decision_for(0))
        self.assertEqual((), ledger.decisions_for(0))

    def test_a_recorded_passing_gate_survives_a_reload_with_exact_versions(
        self,
    ) -> None:
        decision = self.record_stage_zero()

        reloaded = self.repository.load(self.template, TENANT)

        self.assertEqual(
            decision.required_assets, reloaded.decision_for(0).required_assets
        )
        self.assertEqual(decision.asset_approvals, reloaded.decision_for(0).asset_approvals)
        self.assertEqual(TENANT, reloaded.decision_for(0).tenant_id)
        self.assertEqual(TENANT, reloaded.tenant_id)
        self.assertTrue(reloaded.has_passing_decision(0, on=ON))

    def test_history_is_append_only_and_ordered(self) -> None:
        first = self.record_stage_zero()
        second = replace(
            first,
            disposition=GateDisposition.CHANGES_REQUIRED,
            rationale="reopened for a scope correction",
            asset_approvals=(),
        )
        self.repository.append(second)

        reloaded = self.repository.load(self.template, TENANT)

        self.assertEqual((first, second), reloaded.decisions_for(0))
        self.assertFalse(reloaded.has_passing_decision(0, on=ON))

    def test_decisions_are_not_replayed_into_another_clients_ledger(
        self,
    ) -> None:
        self.record_stage_zero()

        other_client = self.repository.load(self.template, "client-other")

        self.assertIsNone(other_client.decision_for(0))

    def test_append_refuses_a_decision_that_carries_no_tenant(self) -> None:
        decision = self.record_stage_zero()

        with self.assertRaises(CrossTenantGateError):
            self.repository.append(replace(decision, tenant_id=""))

    def test_load_requires_a_tenant(self) -> None:
        with self.assertRaises(CrossTenantGateError):
            self.repository.load(self.template, "")

    def test_reload_refuses_a_stored_decision_the_domain_would_reject(
        self,
    ) -> None:
        decision = self.record_stage_zero()
        from redops.contexts.governance.infrastructure.mappers import (
            decision_to_payload,
        )

        payload = decision_to_payload(replace(decision, stage_number=1))
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO gate_decisions (
                    tenant_id, template_version, stage_number,
                    disposition, decided_on, due_on, decision
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    TENANT,
                    self.template.version,
                    1,
                    GateDisposition.APPROVED.value,
                    ON,
                    DUE,
                    self._jsonb(payload),
                ),
            )
        self._connection.commit()

        with self.assertRaises(AssetPackageMismatchError):
            self.repository.load(self.template, TENANT)


if __name__ == "__main__":
    unittest.main()
