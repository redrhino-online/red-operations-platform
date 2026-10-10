"""Named domain errors for the Stage Artifact archive bounded context (pure domain)."""

from __future__ import annotations


class ArchiveError(Exception):
    """Base class for stage artifact archive domain rule violations."""


class BlankArtifactFieldError(ArchiveError, ValueError):
    """A StageArtifact was built without a required non-blank field.

    docs/specs/stage-artifact-archive.md section 1.1: the tenant, workspace,
    kind, asset id, markdown and owner are the artifact's identity and content,
    and an optional note that is present must still say something. An artifact
    that leaves any of them blank cannot be represented as archived content.
    """


class InvalidArtifactStageError(ArchiveError, ValueError):
    """A StageArtifact named a stage outside the canonical 0-10 pipeline.

    docs/specs/stage-artifact-archive.md section 1.1: the archive is organized
    by the stage sequence, so an artifact must name one of the template's
    stages 0-10. A stage outside that sequence has no station to review it.
    """


class InvalidArtifactVersionError(ArchiveError, ValueError):
    """A StageArtifact was built without a positive integer version.

    docs/specs/stage-artifact-archive.md section 1.1: versions order the drops
    of one asset inside the archive, so a versionless or non-positive artifact
    cannot be represented as an archived version.
    """


class UnscopedStageArtifactError(ArchiveError):
    """A stage artifact store was read or written without a tenant.

    docs/specs/stage-artifact-archive.md section 1.1 makes ``tenant_id`` a
    required artifact field taken from the request path, and SPEC.md sections 3
    and 9 make every tenant resource and query carry ``tenant_id``. Storing or
    listing artifacts without a client would either leak across clients or
    create an orphaned record, so the store refuses an unscoped read or write.
    """


class StageArtifactVersionConflictError(ArchiveError):
    """An archived artifact was re-stated under the same key with different content.

    docs/specs/stage-artifact-archive.md section 1.1: the archive is
    append-only, so an identical replay of
    ``(tenant_id, workspace_id, asset_id, version)`` with identical content is
    an idempotent success and the same key with different content is refused —
    a change is dropped as a new version, never a silent rewrite of the
    archived content a review may already have read.
    """
