"""Behavioral tests for the stage artifact store (Archive application).

Rules under test come from docs/specs/stage-artifact-archive.md section 1.1 and
SPEC.md sections 3 and 9:
- The archive is append-only: an identical replay of
  ``(tenant_id, workspace_id, asset_id, version)`` with identical content is an
  idempotent success and the same key with different content is refused with a
  named conflict, so archived content is never rewritten.
- An archived artifact is a client resource: every read and write carries
  ``tenant_id``, and one client's archive cannot be read for another.
- ``next_version`` allocates the next free version for one asset, and ``list``
  orders by stage, kind, asset and newest version first.

The durable PostgreSQL case lives in ``test_stage_artifact_postgres.py`` and
skips cleanly when no psycopg, alembic or ``DATABASE_URL`` is present.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.archive.domain.entities import StageArtifact
from redops.contexts.archive.domain.errors import (
    BlankArtifactFieldError,
    InvalidArtifactStageError,
    InvalidArtifactVersionError,
    StageArtifactVersionConflictError,
    UnscopedStageArtifactError,
)
from redops.contexts.archive.infrastructure.mappers import (
    artifact_from_row,
    artifact_to_row,
)
from redops.contexts.archive.infrastructure.repositories import (
    InMemoryStageArtifactStore,
)

TENANT = "3fmindset"
OTHER_TENANT = "client-other"
WORKSPACE = "ws-3f"
ON = date(2026, 10, 10)


def artifact(
    *,
    tenant_id: str = TENANT,
    workspace_id: str = WORKSPACE,
    stage_number: int = 0,
    kind: str = "signed-scope",
    asset_id: str = "signed-scope",
    version: int = 1,
    markdown: str = "Demo: signed scope\n\n## Scope\n\n- item one\n",
    owner: str = "demo-red-principal",
    note: str | None = None,
    dropped_on: date = ON,
) -> StageArtifact:
    return StageArtifact(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        stage_number=stage_number,
        kind=kind,
        asset_id=asset_id,
        version=version,
        markdown=markdown,
        owner=owner,
        dropped_on=dropped_on,
        note=note,
    )


class StageArtifactEntityTests(unittest.TestCase):
    """The aggregate refuses an artifact its invariants forbid."""

    def test_a_blank_required_field_is_refused(self) -> None:
        for field in (
            "tenant_id",
            "workspace_id",
            "kind",
            "asset_id",
            "markdown",
            "owner",
        ):
            with self.subTest(field=field):
                with self.assertRaises(BlankArtifactFieldError):
                    artifact(**{field: "   "})

    def test_a_stage_outside_the_pipeline_is_refused(self) -> None:
        for stage_number in (-1, 11):
            with self.subTest(stage_number=stage_number):
                with self.assertRaises(InvalidArtifactStageError):
                    artifact(stage_number=stage_number)

    def test_the_stage_bounds_are_inclusive(self) -> None:
        self.assertEqual(0, artifact(stage_number=0).stage_number)
        self.assertEqual(10, artifact(stage_number=10).stage_number)

    def test_a_non_positive_version_is_refused(self) -> None:
        with self.assertRaises(InvalidArtifactVersionError):
            artifact(version=0)

    def test_a_blank_explicit_note_is_refused(self) -> None:
        with self.assertRaises(BlankArtifactFieldError):
            artifact(note="   ")

    def test_an_absent_note_stays_none(self) -> None:
        self.assertIsNone(artifact().note)


class InMemoryStageArtifactStoreTests(unittest.TestCase):
    """The port contract, exercised against the process-local adapter."""

    def setUp(self) -> None:
        self.store = InMemoryStageArtifactStore()

    def test_a_saved_artifact_is_listed_for_its_tenant(self) -> None:
        stored = artifact()

        self.store.save(stored)

        self.assertEqual((stored,), self.store.list(TENANT))

    def test_the_list_is_tenant_scoped(self) -> None:
        self.store.save(artifact())
        self.store.save(artifact(tenant_id=OTHER_TENANT))

        listed = self.store.list(TENANT)

        self.assertEqual(1, len(listed))
        self.assertEqual(TENANT, listed[0].tenant_id)
        self.assertEqual(
            [OTHER_TENANT],
            [item.tenant_id for item in self.store.list(OTHER_TENANT)],
        )

    def test_the_list_orders_by_stage_kind_asset_and_newest_version(self) -> None:
        self.store.save(artifact(kind="intake-questionnaire", asset_id="intake-questionnaire"))
        self.store.save(artifact(version=2))
        self.store.save(artifact(version=1))
        self.store.save(artifact(stage_number=1, kind="avatar-profile", asset_id="avatar-profile"))

        listed = self.store.list(TENANT)

        self.assertEqual(
            [
                (0, "intake-questionnaire", 1),
                (0, "signed-scope", 2),
                (0, "signed-scope", 1),
                (1, "avatar-profile", 1),
            ],
            [
                (item.stage_number, item.kind, item.version)
                for item in listed
            ],
        )

    def test_the_list_applies_the_optional_filters(self) -> None:
        self.store.save(artifact())
        self.store.save(artifact(version=2))
        self.store.save(
            artifact(
                workspace_id="ws-other",
                kind="intake-questionnaire",
                asset_id="intake-questionnaire",
            )
        )
        self.store.save(artifact(stage_number=1, kind="avatar-profile", asset_id="avatar-profile"))

        self.assertEqual(
            3,
            len(self.store.list(TENANT, workspace_id=WORKSPACE)),
        )
        self.assertEqual(
            1,
            len(self.store.list(TENANT, stage_number=1)),
        )
        self.assertEqual(
            1,
            len(self.store.list(TENANT, kind="intake-questionnaire")),
        )
        self.assertEqual(
            2,
            len(self.store.list(TENANT, asset_id="signed-scope")),
        )
        self.assertEqual(
            (2, 1),
            tuple(
                item.version
                for item in self.store.list(
                    TENANT,
                    workspace_id=WORKSPACE,
                    stage_number=0,
                    kind="signed-scope",
                    asset_id="signed-scope",
                )
            ),
        )

    def test_an_identical_replay_is_idempotent(self) -> None:
        stored = artifact()

        self.store.save(stored)
        self.store.save(artifact())

        self.assertEqual(1, len(self.store.list(TENANT)))

    def test_a_different_body_under_the_same_key_is_refused(self) -> None:
        self.store.save(artifact())

        with self.assertRaises(StageArtifactVersionConflictError):
            self.store.save(artifact(markdown="Demo: rewritten scope"))

    def test_the_same_version_of_a_different_asset_is_a_separate_row(self) -> None:
        self.store.save(artifact())
        other = artifact(
            kind="intake-questionnaire",
            asset_id="intake-questionnaire",
            markdown="Demo: intake questionnaire",
        )

        self.store.save(other)

        listed = self.store.list(TENANT)
        self.assertEqual(2, len(listed))
        self.assertEqual(
            other,
            next(item for item in listed if item.asset_id == "intake-questionnaire"),
        )

    def test_next_version_allocates_the_next_free_version(self) -> None:
        self.assertEqual(1, self.store.next_version(TENANT, WORKSPACE, "signed-scope"))

        self.store.save(artifact(version=1))
        self.store.save(artifact(version=2))

        self.assertEqual(3, self.store.next_version(TENANT, WORKSPACE, "signed-scope"))

    def test_next_version_is_scoped_to_the_asset(self) -> None:
        self.store.save(artifact(version=4))

        self.assertEqual(
            1,
            self.store.next_version(TENANT, WORKSPACE, "intake-questionnaire"),
        )
        self.assertEqual(
            1,
            self.store.next_version(TENANT, "ws-other", "signed-scope"),
        )

    def test_a_blank_tenant_is_refused(self) -> None:
        # The entity already refuses a blank tenant at construction (see the
        # entity tests), so the store guard is exercised on the read and
        # version-allocation paths.
        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(UnscopedStageArtifactError):
                    self.store.list(tenant)
                with self.assertRaises(UnscopedStageArtifactError):
                    self.store.next_version(tenant, WORKSPACE, "signed-scope")


class StageArtifactMapperTests(unittest.TestCase):
    def test_an_artifact_round_trips_through_a_row(self) -> None:
        stored = artifact(note="Demo: captured at intake")

        reloaded = artifact_from_row(artifact_to_row(stored))

        self.assertEqual(stored, reloaded)

    def test_an_iso_text_drop_date_round_trips(self) -> None:
        row = artifact_to_row(artifact())
        row = row[:8] + (row[8].isoformat(),) + row[9:]

        reloaded = artifact_from_row(row)

        self.assertEqual(ON, reloaded.dropped_on)

    def test_a_row_the_domain_would_reject_raises(self) -> None:
        row = artifact_to_row(artifact())
        row = row[:6] + ("   ",) + row[7:]

        with self.assertRaises(BlankArtifactFieldError):
            artifact_from_row(row)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
