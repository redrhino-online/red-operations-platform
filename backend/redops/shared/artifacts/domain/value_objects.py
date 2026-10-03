"""Artifact reference value object (SPEC.md section 3).

An ``ArtifactRef`` names the exact private object a URL resolves to: the owning
client, the artifact id, the object store key and the checksum that pins the
bytes. It is a frozen value so a minted URL can never be re-pointed at different
bytes, and its constructor refuses a missing field (SPEC.md sections 3 and 9).
"""

from __future__ import annotations

from dataclasses import dataclass

from redops.shared.artifacts.domain.errors import InvalidArtifactRefError


@dataclass(frozen=True)
class ArtifactRef:
    """An immutable reference to one client's stored artifact bytes."""

    tenant_id: str
    artifact_id: str
    object_key: str
    checksum: str

    def __post_init__(self) -> None:
        for label, value in (
            ("artifact tenant id", self.tenant_id),
            ("artifact id", self.artifact_id),
            ("artifact object key", self.object_key),
            ("artifact checksum", self.checksum),
        ):
            if not value or not value.strip():
                raise InvalidArtifactRefError(f"{label} is required")
