"""Build lifecycle policy for the Production bounded context (pure domain).

Encodes SPEC.md section 3: a BuildObject moves through its lifecycle states and
illegal transitions are rejected rather than silently coerced.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import ProvenanceClass
from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.production.domain.entities import AuthorityAmplifier
from redops.contexts.production.domain.errors import (
    AuthorityAmplifierDependencyError,
    IllegalBuildTransitionError,
    UnsupportedProofError,
)
from redops.contexts.production.domain.value_objects import BuildState


class BuildTransitionPolicy:
    """Legal BuildObject state transitions (SPEC.md sections 3 and 4)."""

    ALLOWED: Mapping[BuildState, frozenset[BuildState]] = {
        BuildState.IDENTIFIED: frozenset(
            {
                BuildState.SOURCE_REQUIRED,
                BuildState.READY,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.SOURCE_REQUIRED: frozenset(
            {BuildState.READY, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.READY: frozenset(
            {
                BuildState.IN_DEVELOPMENT,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.IN_DEVELOPMENT: frozenset(
            {
                BuildState.INTERNAL_REVIEW,
                BuildState.CHANGES_REQUIRED,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.INTERNAL_REVIEW: frozenset(
            {
                BuildState.CLIENT_REVIEW,
                BuildState.CHANGES_REQUIRED,
                BuildState.APPROVED,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.CLIENT_REVIEW: frozenset(
            {
                BuildState.CHANGES_REQUIRED,
                BuildState.APPROVED,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.CHANGES_REQUIRED: frozenset(
            {
                BuildState.IN_DEVELOPMENT,
                BuildState.READY,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.APPROVED: frozenset(
            {
                BuildState.PRODUCTION_READY,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.PRODUCTION_READY: frozenset(
            {BuildState.DEPLOYED, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.DEPLOYED: frozenset(
            {BuildState.MEASURING, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.MEASURING: frozenset(
            {BuildState.OPTIMIZING, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.OPTIMIZING: frozenset(
            {BuildState.MEASURING, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.SUPERSEDED: frozenset({BuildState.ARCHIVED}),
        BuildState.ARCHIVED: frozenset(),
    }

    def can_transition(self, current: BuildState, target: BuildState) -> bool:
        return target in self.ALLOWED.get(current, frozenset())

    def require(self, current: BuildState, target: BuildState) -> None:
        if not self.can_transition(current, target):
            raise IllegalBuildTransitionError(
                f"cannot transition build from {current.value!r} to {target.value!r}"
            )


class AuthorityAmplifierPolicy:
    """Refuses stage 7 script approval on an under-grounded amplifier.

    SPEC.md section 4, stage 7 "Produce" and its "Authority Amplifier Approved"
    checkpoint: the message and supported proof pass review before visual or
    video production. The amplifier must be grounded on an approved stage 6
    `CampaignMessage` and an approved method for the tenant, and every proof
    claim must be a claim of that method backed by a known, directly sourced
    knowledge claim. This is the Production-side reading of SPEC.md section 3
    "Production requires approved dependencies" and the Phase 4 TDD example
    "unsupported proof is flagged".
    """

    def require_script_approvable(
        self,
        amplifier: AuthorityAmplifier,
        approved_methods: Iterable[MethodVersion],
        claims: Iterable[Claim],
    ) -> None:
        if amplifier.state.is_terminal:
            raise AuthorityAmplifierDependencyError(
                f"terminal authority amplifier {amplifier.amplifier_id!r} cannot "
                "approve its script"
            )
        message = amplifier.message
        if message.tenant_id != amplifier.tenant_id:
            raise AuthorityAmplifierDependencyError(
                "an authority amplifier cannot be grounded on another tenant's "
                "message"
            )
        if not message.is_approved:
            raise AuthorityAmplifierDependencyError(
                f"authority amplifier {amplifier.amplifier_id!r} cannot approve "
                "its script: it is grounded on a stage 6 message that is not "
                "approved"
            )
        methods = tuple(approved_methods)
        method = self._authorizing_method(amplifier, methods)
        if method is None:
            raise AuthorityAmplifierDependencyError(
                f"authority amplifier {amplifier.amplifier_id!r} cannot approve "
                "its script: its message method is not an approved dependency "
                "for this tenant"
            )
        supported = {
            claim.claim_id
            for claim in claims
            if claim.tenant_id == amplifier.tenant_id
            and claim.provenance is ProvenanceClass.KNOWN
        }
        for claim_id in sorted(amplifier.proof_claim_ids):
            if claim_id not in method.claims:
                raise UnsupportedProofError(
                    f"authority amplifier {amplifier.amplifier_id!r} proof "
                    f"{claim_id!r} is not a claim of the approved method"
                )
            if claim_id not in supported:
                raise UnsupportedProofError(
                    f"authority amplifier {amplifier.amplifier_id!r} proof "
                    f"{claim_id!r} is not backed by a known, directly sourced "
                    "claim"
                )

    @staticmethod
    def _authorizing_method(
        amplifier: AuthorityAmplifier, methods: tuple[MethodVersion, ...]
    ) -> MethodVersion | None:
        reference = amplifier.message.method_reference
        for method in methods:
            if (
                method.method_id == reference.method_id
                and method.tenant_id == amplifier.tenant_id
                and method.authorizes(reference.version, reference.intended_use)
            ):
                return method
        return None
