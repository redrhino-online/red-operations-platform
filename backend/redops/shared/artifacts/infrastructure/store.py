"""Reference adapter for the tenant-scoped artifact URL seam.

``InMemoryArtifactUrlResolver`` is the process-local reference implementation of
``ArtifactUrlResolver``: it mints an opaque URL per ``ArtifactRef`` and resolves
it only inside the client the artifact belongs to. A URL minted for one client
never resolves for another, even with the exact string, and an unknown URL
resolves to ``None`` so the layer discloses neither the bytes nor the existence
of another client's artifact (SPEC.md sections 3, 9 and 13 condition 3). A
durable private-object-store adapter implements the same port; the object-store
provisioner is a SPEC.md section 11 decision still to settle, so only the
reference adapter exists today.
"""

from __future__ import annotations

from redops.shared.artifacts.application.ports import ArtifactUrlResolver
from redops.shared.artifacts.domain.errors import ArtifactTenantBoundaryError
from redops.shared.artifacts.domain.value_objects import ArtifactRef


def _require_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped mint or read of a client's artifact URL."""

    if not value or not value.strip():
        raise ArtifactTenantBoundaryError(
            f"an artifact URL {operation} requires a non-blank tenant id; an "
            "artifact is a client resource and cannot be minted or resolved "
            "unscoped"
        )


class InMemoryArtifactUrlResolver(ArtifactUrlResolver):
    """Process-local, client-scoped artifact URL resolver."""

    def __init__(self) -> None:
        self._by_url: dict[str, ArtifactRef] = {}
        self._count = 0

    def mint(self, artifact: ArtifactRef) -> str:
        self._count += 1
        url = (
            f"artifact://{artifact.tenant_id}/{artifact.artifact_id}"
            f"/{self._count}"
        )
        self._by_url[url] = artifact
        return url

    def resolve(self, tenant_id: str, url: str) -> ArtifactRef | None:
        _require_tenant(tenant_id, "resolve")
        artifact = self._by_url.get(url)
        if artifact is None or artifact.tenant_id != tenant_id:
            return None
        return artifact
