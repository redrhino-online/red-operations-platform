"""Cross-tenant isolation for the artifact URL layer.

SPEC.md section 13 condition 3 requires the cross-tenant security suite to cover
the artifact URL layer, and SPEC.md section 9 requires cross-client access to be
refused at that layer. These tests exercise the shared ``ArtifactUrlResolver``
port through its tenant-scoped reference adapter: a URL minted for one client
never resolves for another, and an unknown or forged URL resolves to ``None`` so
the layer discloses neither another client's bytes nor the existence of its
artifact.

The durable private-object-store adapter implements the same port once the
object-store provisioner is chosen (SPEC.md section 11), without changing these
callers.
"""

from __future__ import annotations

import unittest

from redops.shared.artifacts.domain.errors import (
    ArtifactTenantBoundaryError,
    InvalidArtifactRefError,
)
from redops.shared.artifacts.domain.value_objects import ArtifactRef
from redops.shared.artifacts.infrastructure.store import (
    InMemoryArtifactUrlResolver,
)

TENANT = "3fmindset"
OTHER_TENANT = "client-other"


def artifact(artifact_id: str, tenant_id: str) -> ArtifactRef:
    return ArtifactRef(
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        object_key=f"redops-private/{tenant_id}/{artifact_id}",
        checksum=f"sha256:{artifact_id}",
    )


class ArtifactUrlIsolationTests(unittest.TestCase):
    def setUp(self):
        self.resolver = InMemoryArtifactUrlResolver()
        self.artifact = artifact("aa-final.mp4", TENANT)
        self.url = self.resolver.mint(self.artifact)

    def test_a_client_resolves_its_own_minted_url_to_the_exact_artifact(self):
        self.assertEqual(self.artifact, self.resolver.resolve(TENANT, self.url))

    def test_a_url_minted_for_another_client_never_resolves_here(self):
        other_url = self.resolver.mint(artifact("other-secret.pdf", OTHER_TENANT))

        self.assertIsNone(self.resolver.resolve(TENANT, other_url))

    def test_this_clients_url_still_resolves_for_its_own_client(self):
        other_url = self.resolver.mint(artifact("other-secret.pdf", OTHER_TENANT))

        self.assertEqual(OTHER_TENANT, self.resolver.resolve(OTHER_TENANT, other_url).tenant_id)
        self.assertEqual(self.artifact, self.resolver.resolve(TENANT, self.url))

    def test_an_unknown_or_forged_url_resolves_to_nothing(self):
        forged = self.url + "-forged"

        self.assertIsNone(self.resolver.resolve(TENANT, forged))
        self.assertIsNone(self.resolver.resolve(TENANT, "artifact://nowhere"))

    def test_an_unscoped_artifact_cannot_be_minted(self):
        with self.assertRaises(InvalidArtifactRefError):
            self.resolver.mint(artifact("orphan.mp4", "   "))

    def test_a_blank_tenant_is_refused_when_resolving(self):
        with self.assertRaises(ArtifactTenantBoundaryError):
            self.resolver.resolve("   ", self.url)


class ArtifactRefInvariantTests(unittest.TestCase):
    def test_a_reference_without_identity_or_checksum_is_refused(self):
        with self.assertRaises(InvalidArtifactRefError):
            ArtifactRef(
                tenant_id=TENANT,
                artifact_id="no-checksum.mp4",
                object_key="redops-private/3fmindset/no-checksum.mp4",
                checksum="",
            )


if __name__ == "__main__":
    unittest.main()
