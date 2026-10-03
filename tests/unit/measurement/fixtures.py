"""Shared pure-domain fixtures for Measurement tests.

These build a stage 10 improvement proposal grounded on an established
same-tenant ``PerformanceBaseline``, the named-owner approval that moves it out
of proposal, and a before/after ``ImprovementOutcome``, so tests that exercise
the improvement loop do not restate the same content in every file. They are
test data only and carry no behavior.
"""

from __future__ import annotations

from redops.contexts.measurement.domain.entities import ImprovementProposal
from redops.contexts.measurement.domain.value_objects import (
    ImprovementApproval,
    ImprovementOutcome,
)
from redops.contexts.execution.domain.value_objects import ClaimKind

from ..execution.fixtures import (
    TODAY,
    established_baseline,
    performance_claim,
)

TENANT = "client-3f"


def improvement_proposal(baseline=None, **overrides) -> ImprovementProposal:
    values = {
        "proposal_id": "improve-3f",
        "tenant_id": TENANT,
        "baseline": established_baseline() if baseline is None else baseline,
        "proposed_by": "optimizer-agent",
        "owner": "performance-owner",
        "subject": "cost per lead",
        "lever": "landing page headline",
        "evidence": "evidence://baseline/cost-per-lead-analysis",
        "measurement_plan": "compare cost per lead two weeks before and after",
    }
    values.update(overrides)
    return ImprovementProposal(**values)


def improvement_approval(**overrides) -> ImprovementApproval:
    values = {
        "approved_by": "performance-owner",
        "intended_use": "apply the lever to the live campaign",
        "approved_on": TODAY,
    }
    values.update(overrides)
    return ImprovementApproval(**values)


def approved_improvement(**overrides) -> ImprovementProposal:
    return improvement_proposal(**overrides).approve(
        approval=improvement_approval()
    )


def improvement_outcome(**overrides) -> ImprovementOutcome:
    values = {
        "outcome_id": "outcome-3f",
        "tenant_id": TENANT,
        "before": performance_claim(
            claim_id="before-3f",
            subject="cost per lead",
            statement="cost per lead was twelve dollars",
            kind=ClaimKind.OBSERVATION,
        ),
        "after": performance_claim(
            claim_id="after-3f",
            subject="cost per lead",
            statement="cost per lead was eight dollars",
            kind=ClaimKind.OBSERVATION,
        ),
        "measured_on": TODAY,
        "summary": "cost per lead fell after the headline change",
    }
    values.update(overrides)
    return ImprovementOutcome(**values)


def measured_improvement(**overrides) -> ImprovementProposal:
    return approved_improvement(**overrides).record_outcome(
        outcome=improvement_outcome()
    )
