"""Row serialisation for the ``StageArtifactStore`` port.

The durable adapter stores the artifact's fields as typed columns (docs/specs/
stage-artifact-archive.md section 1.2), so the mappers translate between the
``StageArtifact`` aggregate and one table row. A reloaded row is re-validated
through the aggregate rather than trusted as stored: a stored row the aggregate
would reject raises on load instead of being read back as a real artifact.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from redops.contexts.archive.domain.entities import StageArtifact

STAGE_ARTIFACT_COLUMNS: tuple[str, ...] = (
    "tenant_id",
    "workspace_id",
    "stage_number",
    "kind",
    "asset_id",
    "version",
    "markdown",
    "owner",
    "dropped_on",
    "note",
)


def artifact_to_row(artifact: StageArtifact) -> tuple[Any, ...]:
    """Serialise an archived artifact into the table's typed column order."""

    return (
        artifact.tenant_id,
        artifact.workspace_id,
        artifact.stage_number,
        artifact.kind,
        artifact.asset_id,
        artifact.version,
        artifact.markdown,
        artifact.owner,
        artifact.dropped_on,
        artifact.note,
    )


def artifact_from_row(row: tuple[Any, ...]) -> StageArtifact:
    """Rebuild an archived artifact from a stored row, re-validating its fields.

    ``dropped_on`` arrives as a ``date`` from the driver and as ISO text from a
    serialised payload, so both shapes rebuild into the typed value.
    """

    dropped_on = row[8]
    if not isinstance(dropped_on, date):
        dropped_on = date.fromisoformat(dropped_on)
    return StageArtifact(
        tenant_id=row[0],
        workspace_id=row[1],
        stage_number=row[2],
        kind=row[3],
        asset_id=row[4],
        version=row[5],
        markdown=row[6],
        owner=row[7],
        dropped_on=dropped_on,
        note=row[9],
    )
