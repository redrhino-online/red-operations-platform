"""Named domain errors for the shared artifact-access layer (SPEC.md sections 3 and 9)."""

from __future__ import annotations


class ArtifactError(Exception):
    """Base class for artifact-access rule violations."""


class InvalidArtifactRefError(ArtifactError, ValueError):
    """An ArtifactRef was built without the identity or evidence it requires.

    SPEC.md section 3 makes object bytes immutable and traceable: an artifact
    reference must carry its owning client, its id, the private object key and
    the checksum that pins the exact bytes. A reference missing any of these
    cannot be resolved to a verified original, so it is refused at construction
    rather than minted into a URL that would resolve to nothing verifiable.
    """


class ArtifactTenantBoundaryError(ArtifactError):
    """An artifact URL was minted or resolved without a client scope.

    SPEC.md sections 3 and 9 make every tenant resource and query carry
    ``tenant_id``, and SPEC.md section 13 condition 3 requires cross-client
    access to be refused at the artifact URL layer. Resolving an artifact URL
    without a client could leak one client's bytes, so it is refused rather than
    answered unscoped. An artifact reference itself already refuses a blank
    client at construction (``InvalidArtifactRefError``).
    """
