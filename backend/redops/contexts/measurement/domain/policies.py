"""Approval and measurement policy for the stage 10 improvement loop (pure domain).

SPEC.md section 4, stage 10: "performance recommendations require evidence and
owner approval before material changes". An improvement stays a proposal until a
named human owner approves it, and only an approved improvement grounded on the
same established same-tenant baseline can be measured. This mirrors the owner and
designated-authority separation used for the launch and baseline gates.
"""

from __future__ import annotations

from redops.contexts.measurement.domain.entities import ImprovementProposal
from redops.contexts.measurement.domain.errors import (
    ImprovementAuthorityError,
    ImprovementDependencyError,
    ImprovementNotApprovedError,
    ImprovementOutcomeSupportError,
    ImprovementStateError,
)
from redops.contexts.measurement.domain.value_objects import (
    ImprovementApproval,
    ImprovementOutcome,
    ImprovementState,
)


class ImprovementApprovalPolicy:
    """Refuses an improvement approval that is out of state or not the owner's.

    SPEC.md section 4: a performance recommendation becomes a material change
    only when a named human owner approves it, and an agent cannot confer human
    approval upon itself. A rejected or already-decided proposal cannot be
    approved, and the approval must come from the proposal's owner rather than the
    proposer or anyone else.
    """

    def require(
        self, proposal: ImprovementProposal, approval: ImprovementApproval
    ) -> None:
        if proposal.state.is_terminal:
            raise ImprovementStateError(
                f"terminal improvement {proposal.proposal_id!r} cannot be "
                "approved"
            )
        if proposal.state is not ImprovementState.PROPOSED:
            raise ImprovementStateError(
                f"improvement {proposal.proposal_id!r} is "
                f"{proposal.state.value!r} and cannot be approved again"
            )
        if not proposal.baseline.is_established:
            raise ImprovementDependencyError(
                f"improvement {proposal.proposal_id!r} cannot be approved: its "
                "performance baseline is no longer established"
            )
        if approval.approved_by != proposal.owner:
            raise ImprovementAuthorityError(
                f"improvement {proposal.proposal_id!r} was not approved by its "
                f"named owner {proposal.owner!r}"
            )
        if approval.approved_by == proposal.proposed_by:
            raise ImprovementAuthorityError(
                "the improvement proposer cannot approve its own proposal"
            )


class ImprovementMeasurementPolicy:
    """Refuses an outcome on an unapproved or ungrounded improvement.

    SPEC.md sections 3 and 4: only an approved improvement can be measured, and
    the before-and-after must be grounded on the same established same-tenant
    baseline the improvement was approved against so the observed movement stays
    traceable and distinct from a causal conclusion.
    """

    def require(
        self, proposal: ImprovementProposal, outcome: ImprovementOutcome
    ) -> None:
        if proposal.state is not ImprovementState.APPROVED:
            raise ImprovementNotApprovedError(
                f"improvement {proposal.proposal_id!r} is "
                f"{proposal.state.value!r}; only an owner-approved improvement "
                "can be measured"
            )
        if proposal.baseline.tenant_id != outcome.tenant_id:
            raise ImprovementOutcomeSupportError(
                f"improvement {proposal.proposal_id!r} is grounded on tenant "
                f"{proposal.baseline.tenant_id!r}, but the outcome belongs to "
                f"tenant {outcome.tenant_id!r}"
            )
        if not proposal.baseline.is_established:
            raise ImprovementDependencyError(
                f"improvement {proposal.proposal_id!r} cannot be measured: its "
                "performance baseline is no longer established"
            )
        baseline_id = proposal.baseline.baseline_id
        for label, claim in (("before", outcome.before), ("after", outcome.after)):
            if claim.baseline_id != baseline_id:
                raise ImprovementOutcomeSupportError(
                    f"the improvement outcome {label} observation must cite the "
                    f"approved baseline {baseline_id!r}"
                )
