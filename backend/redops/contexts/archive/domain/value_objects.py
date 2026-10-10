"""Value objects for the Stage Artifact archive bounded context (pure domain)."""

from __future__ import annotations

from redops.contexts.archive.domain.errors import BlankArtifactFieldError


def require_artifact_text(value: str, label: str) -> str:
    """Refuse a blank required artifact field (the ``_require_intake_text`` pattern).

    docs/specs/stage-artifact-archive.md section 1.1 requires the artifact's
    identity and content fields to be non-blank, so a whitespace-only value is
    the same as a missing one and is refused with the named error rather than
    being stored as empty content.
    """

    if not value or not value.strip():
        raise BlankArtifactFieldError(f"{label} is required")
    return value
