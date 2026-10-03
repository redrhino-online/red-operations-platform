"""Application port for tenant-scoped artifact URL access (SPEC.md sections 3, 6 and 9).

SPEC.md section 3 keeps object bytes in a private object store and the original
retrievable only to authorized users; SPEC.md section 9 requires cross-client
access to be tested at the artifact URL layer; SPEC.md section 13 condition 3
names that layer. The port is defined by that need: mint a scoped URL for one
client's artifact, and resolve a URL only inside the client it was minted for. A
URL minted for another client never resolves, and an unknown or forged URL
resolves to ``None`` rather than disclosing that some other client owns it.
"""

from __future__ import annotations

import abc

from redops.shared.artifacts.domain.value_objects import ArtifactRef


class ArtifactUrlResolver(abc.ABC):
    """Seam for minting and resolving tenant-scoped artifact URLs.

    ``mint`` returns an opaque, client-scoped URL for an artifact reference;
    ``resolve`` returns the reference only when the URL was minted for the
    requested tenant, and ``None`` for an unknown URL or one owned by another
    client. SPEC.md sections 3 and 9 require every artifact read to carry the
    client scope, so a blank tenant is refused rather than resolved unscoped.
    ``close`` releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def mint(self, artifact: ArtifactRef) -> str:
        """Return an opaque URL scoped to the artifact's owning client."""

    @abc.abstractmethod
    def resolve(self, tenant_id: str, url: str) -> ArtifactRef | None:
        """Return the tenant's artifact for ``url``, or ``None`` if not theirs."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
