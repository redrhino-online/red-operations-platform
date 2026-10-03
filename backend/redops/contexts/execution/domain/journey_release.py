"""The ``JourneyRelease`` core aggregate (Execution domain, pure domain).

SPEC.md section 3 names ``JourneyRelease`` (assets, routing, configuration
digest, rollback ref) as a core aggregate with the invariant "Launch needs
signed readiness and authorized release", and SPEC.md section 4 requires launch
to have "integration checks, customer path dry run, consent where applicable,
named operator" and "rollback". This value object is the RED-owned release
record that ties an authorized stage 9 launch QA to the exact asset versions it
releases, the routing configuration digest and the rollback reference.

The release is grounded on the reviewed stage 9 ``LaunchQA`` (SPEC.md section 4,
"Launch Approved"), which already carries the signed human ``TrafficAuthorization``
when it reached ``READY_FOR_TRAFFIC``. The release refuses to exist unless the QA
is signed ready, the QA's pinned authorization names the QA's designated
authority, every released asset belongs to the same tenant and the package pins
exactly one exact version per kind, and routing, configuration digest and
rollback reference are present. It is frozen: approval pins the exact evidence
and a later release is a new identity, so a previous deployed release stays
historically identifiable (SPEC.md sections 3 and 4).

It carries no execution permission: it authorizes the operator to begin, which
is a human decision recorded elsewhere, and it never asserts that traffic is
live, which is a stage 10 observation. The canon has no dedicated journey
release file, so the shape is governed by the SPEC (SPEC.md section 12.1).
"""

from __future__ import annotations

from dataclasses import dataclass

from redops.contexts.execution.domain.entities import LaunchQA
from redops.contexts.execution.domain.errors import (
    InvalidJourneyReleaseError,
    JourneyReleaseAuthorityError,
    JourneyReleaseDependencyError,
    JourneyReleaseReadinessError,
    JourneyReleaseTenantBoundaryError,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion


@dataclass(frozen=True)
class JourneyRelease:
    """An authorized release of one client's journey (SPEC.md sections 3 and 4).

    ``assets`` pins the exact ``StageAssetVersion`` evidence being released,
    ``routing`` and ``configuration_digest`` identify the deployed routing and
    configuration, and ``rollback_ref`` names the previous compatible state the
    operator can revert to. The aggregate only exists once the stage 9 launch QA
    it is grounded on is signed ready for traffic and carries an authorization
    by the QA's designated authority, so the invariant "launch needs signed
    readiness and authorized release" is enforced at construction.
    """

    release_id: str
    tenant_id: str
    qa: LaunchQA
    assets: tuple[StageAssetVersion, ...]
    routing: str
    configuration_digest: str
    rollback_ref: str

    def __post_init__(self) -> None:
        for label, value in (
            ("journey release id", self.release_id),
            ("journey release tenant id", self.tenant_id),
            ("journey release routing", self.routing),
            ("journey release configuration digest", self.configuration_digest),
            ("journey release rollback ref", self.rollback_ref),
        ):
            if not value or not value.strip():
                raise InvalidJourneyReleaseError(f"{label} is required")

        if not isinstance(self.qa, LaunchQA):
            raise JourneyReleaseDependencyError(
                "a journey release must be grounded on a typed stage 9 "
                "LaunchQA, not an untyped readiness claim"
            )
        if self.qa.tenant_id != self.tenant_id:
            raise JourneyReleaseTenantBoundaryError(
                f"journey release {self.release_id!r} is scoped to tenant "
                f"{self.tenant_id!r} but is grounded on launch QA "
                f"{self.qa.qa_id!r} of tenant {self.qa.tenant_id!r}"
            )

        if not self.qa.is_ready_for_traffic:
            raise JourneyReleaseReadinessError(
                f"launch QA {self.qa.qa_id!r} has not passed Launch Approved, "
                "so it cannot authorize a journey release"
            )
        authorization = self.qa.authorization
        if authorization is None:
            raise JourneyReleaseReadinessError(
                f"launch QA {self.qa.qa_id!r} carries no traffic authorization, "
                "so it has no authorized release to pin"
            )
        if authorization.authorized_by != self.qa.designated_authority:
            raise JourneyReleaseAuthorityError(
                f"journey release {self.release_id!r} pins a traffic "
                f"authorization by {authorization.authorized_by!r}, not the "
                f"designated authority {self.qa.designated_authority!r}"
            )

        if not self.assets:
            raise InvalidJourneyReleaseError(
                "a journey release must pin the exact versions of the assets it "
                "releases"
            )
        seen_kinds: set[str] = set()
        for asset in self.assets:
            if not isinstance(asset, StageAssetVersion):
                raise InvalidJourneyReleaseError(
                    "a journey release pins StageAssetVersion evidence, not "
                    f"untyped {type(asset).__name__}"
                )
            if asset.tenant_id != self.tenant_id:
                raise JourneyReleaseTenantBoundaryError(
                    f"journey release {self.release_id!r} pins asset "
                    f"{asset.asset_id!r} of tenant {asset.tenant_id!r}, not "
                    f"release tenant {self.tenant_id!r}"
                )
            if asset.kind in seen_kinds:
                raise InvalidJourneyReleaseError(
                    f"journey release {self.release_id!r} pins more than one "
                    f"version for kind {asset.kind!r}; a release needs exactly "
                    "one exact version per kind"
                )
            seen_kinds.add(asset.kind)

    @property
    def released_kinds(self) -> frozenset[str]:
        """The asset kinds whose exact versions this release pins."""
        return frozenset(asset.kind for asset in self.assets)

    @property
    def is_signed_ready(self) -> bool:
        """Whether the grounding QA is signed ready for traffic."""
        return self.qa.is_ready_for_traffic

    @property
    def is_authorized(self) -> bool:
        """Whether the grounding QA pins an authorization by its authority."""
        return (
            self.qa.authorization is not None
            and self.qa.authorization.authorized_by
            == self.qa.designated_authority
        )
