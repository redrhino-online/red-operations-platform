"""Aggregates for the Stage Artifact archive bounded context (pure domain).

StageArtifact is one dropped markdown artifact of the stage 0-10 pipeline
(docs/specs/stage-artifact-archive.md section 1.1). It is a frozen,
reject-only value: the archive collects and preserves what was dropped, so an
artifact that leaves its tenant, workspace, stage, kind, asset, version,
markdown or owner unspecified cannot be represented as archived content, and a
change is a new version rather than a rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from redops.contexts.archive.domain.errors import (
    BlankArtifactFieldError,
    InvalidArtifactStageError,
    InvalidArtifactVersionError,
)
from redops.contexts.archive.domain.value_objects import require_artifact_text

MIN_STAGE_NUMBER = 0
MAX_STAGE_NUMBER = 10


@dataclass(frozen=True)
class StageArtifact:
    """One archived stage artifact: markdown content dropped at a stage.

    The tenant comes from the request path, never the body, and the workspace
    must exist in the engagement workspace store (resolved by the entry point).
    The kind is free text — the stage template's canonical kinds are offered as
    options but the archive collects everything — and the asset id defaults to
    the kind when omitted. The version is a positive integer that orders the
    drops of one asset, the markdown is the artifact content itself, the owner
    is collection attribution (not domain-validated authority), ``dropped_on``
    is the collection date and the note is optional. The aggregate is
    append-only: no update or delete path exists.
    """

    tenant_id: str
    workspace_id: str
    stage_number: int
    kind: str
    asset_id: str
    version: int
    markdown: str
    owner: str
    dropped_on: date
    note: str | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("stage artifact tenant id", self.tenant_id),
            ("stage artifact workspace id", self.workspace_id),
            ("stage artifact kind", self.kind),
            ("stage artifact asset id", self.asset_id),
            ("stage artifact markdown", self.markdown),
            ("stage artifact owner", self.owner),
        ):
            require_artifact_text(value, label)
        if not isinstance(self.stage_number, int) or not (
            MIN_STAGE_NUMBER <= self.stage_number <= MAX_STAGE_NUMBER
        ):
            raise InvalidArtifactStageError(
                f"stage artifact stage number must be between "
                f"{MIN_STAGE_NUMBER} and {MAX_STAGE_NUMBER}, got "
                f"{self.stage_number!r}"
            )
        if not isinstance(self.version, int) or self.version < 1:
            raise InvalidArtifactVersionError(
                "a stage artifact requires a positive integer version, got "
                f"{self.version!r}"
            )
        if self.note is not None:
            require_artifact_text(self.note, "stage artifact note")
        if not isinstance(self.dropped_on, date):
            raise BlankArtifactFieldError(
                "stage artifact dropped_on date is required"
            )
