"""Behavioral tests for the stage 10 improvement loop (Measurement domain).

Rules under test come from SPEC.md section 4 ("performance recommendations
require evidence and owner approval before material changes"; stage 10 continues
into Optimization after the performance baseline is established) and Phase 5
("one improvement is approved and measured"), shaped by the canon discipline
that optimization starts only after a baseline exists and changes one variable at
a time so the movement can be attributed (canon files 23 and 24):

- An optimization stays a proposal until a named human owner approves it; the
  proposer cannot approve its own proposal.
- A proposal must be grounded on an established same-tenant performance baseline.
- Only an approved improvement can be measured, and the before/after outcome is
  grounded on that same baseline for the same tenant.
- The recorded movement is an observation, kept distinct from a causal
  conclusion (SPEC.md section 3 Measurement invariant).
- The before observation window must end before the after window starts, so a
  recorded movement is temporally sound and an after-state is never read from
  before or during its own before-state (canon file 24: wait before reading how
  the change did).
- The before observation window must close on or before the owner approval date,
  so the pre-change measurement is a genuinely pre-change baseline rather than a
  period observed after the material change was authorized (canon files 23 and
  24).
- The after observation window must have closed by the outcome's ``measured_on``
  date, so a result is not read before the window it is measured over has
  elapsed (canon file 24: "I wait 10 days to see how it does"; "don't touch
  anything for 10 days").
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.measurement.domain.entities import ImprovementProposal
from redops.contexts.measurement.domain.errors import (
    ImprovementApprovalPrecedenceError,
    ImprovementAuthorityError,
    ImprovementBeforeWindowError,
    ImprovementDependencyError,
    ImprovementNotApprovedError,
    ImprovementObservationError,
    ImprovementObservationWindowError,
    ImprovementOutcomeSupportError,
    ImprovementResultWindowOpenError,
    ImprovementStateError,
    InvalidImprovementError,
    InvalidImprovementOutcomeError,
)
from redops.contexts.measurement.domain.value_objects import (
    ImprovementState,
    MeasurementBasis,
    MeasurementWindow,
)
from redops.contexts.execution.domain.value_objects import ClaimKind

from ..execution.fixtures import (
    established_baseline,
    performance_baseline,
)
from .fixtures import (
    TENANT,
    approved_improvement,
    improvement_approval,
    improvement_outcome,
    improvement_proposal,
    measured_improvement,
    measurement_record,
    metric_definition,
)


class ImprovementProposalTests(unittest.TestCase):
    def test_a_grounded_proposal_starts_proposed(self):
        proposal = improvement_proposal()

        self.assertIs(ImprovementState.PROPOSED, proposal.state)
        self.assertFalse(proposal.is_approved)
        self.assertFalse(proposal.is_measured)
        self.assertIsNone(proposal.approval)

    def test_a_proposal_requires_its_identification_fields(self):
        for field in (
            "proposal_id",
            "tenant_id",
            "proposed_by",
            "owner",
            "subject",
            "lever",
            "evidence",
            "measurement_plan",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidImprovementError):
                    improvement_proposal(**{field: "  "})

    def test_a_proposal_cannot_be_grounded_on_another_tenants_baseline(self):
        with self.assertRaises(ImprovementDependencyError):
            improvement_proposal(
                proposal_id="improve-foreign",
                tenant_id="client-other",
                metric=metric_definition(tenant_id="client-other"),
            )

    def test_a_proposal_cannot_be_grounded_on_a_draft_baseline(self):
        with self.assertRaises(ImprovementDependencyError):
            improvement_proposal(baseline=performance_baseline())

    def test_a_proposal_cannot_be_grounded_on_a_review_required_baseline(self):
        review = established_baseline().mark_review_required(
            reason="upstream launch changed"
        )

        with self.assertRaises(ImprovementDependencyError):
            improvement_proposal(baseline=review)

    def test_the_proposer_cannot_also_be_the_named_approving_owner(self):
        with self.assertRaises(ImprovementAuthorityError):
            improvement_proposal(proposed_by="performance-owner")

    def test_a_proposal_is_immutable(self):
        proposal = improvement_proposal()

        with self.assertRaises(FrozenInstanceError):
            proposal.owner = "tampered"

    def test_a_proposal_names_the_single_lever_and_evidence(self):
        with self.assertRaises(InvalidImprovementError):
            ImprovementProposal(
                proposal_id="improve-blank-lever",
                tenant_id=TENANT,
                baseline=established_baseline(),
                metric=metric_definition(),
                proposed_by="optimizer-agent",
                owner="performance-owner",
                subject="cost per lead",
                lever="   ",
                evidence="evidence://baseline/cost-per-lead-analysis",
                measurement_plan="compare cost per lead",
            )


class ImprovementApprovalTests(unittest.TestCase):
    def test_the_named_owner_approval_moves_the_proposal_to_approved(self):
        approved = improvement_proposal().approve(
            approval=improvement_approval()
        )

        self.assertIs(ImprovementState.APPROVED, approved.state)
        self.assertTrue(approved.is_approved)
        self.assertIsNotNone(approved.approval)

    def test_an_approval_from_someone_other_than_the_owner_is_refused(self):
        with self.assertRaises(ImprovementAuthorityError):
            improvement_proposal().approve(
                approval=improvement_approval(approved_by="someone-else")
            )

    def test_the_proposer_cannot_approve_its_own_proposal(self):
        from .fixtures import improvement_approval as approval_factory

        proposal = improvement_proposal(proposed_by="owner-agent")

        with self.assertRaises(ImprovementAuthorityError):
            proposal.approve(
                approval=approval_factory(approved_by="owner-agent")
            )

    def test_a_rejected_proposal_cannot_be_approved(self):
        rejected = improvement_proposal().reject(reason="not worth the change")

        with self.assertRaises(ImprovementStateError):
            rejected.approve(approval=improvement_approval())

    def test_an_already_approved_proposal_cannot_be_approved_again(self):
        with self.assertRaises(ImprovementStateError):
            approved_improvement().approve(approval=improvement_approval())

    def test_an_approval_requires_an_authority_and_an_intended_use(self):
        from redops.contexts.measurement.domain.value_objects import (
            ImprovementApproval,
        )

        for field in ("approved_by", "intended_use"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidImprovementError):
                    ImprovementApproval(
                        **{
                            "approved_by": "performance-owner",
                            "intended_use": "apply the lever",
                            "approved_on": improvement_approval().approved_on,
                            field: "  ",
                        }
                    )


class ImprovementMeasurementTests(unittest.TestCase):
    def test_an_approved_improvement_records_a_measured_outcome(self):
        measured = approved_improvement().record_outcome(
            outcome=improvement_outcome()
        )

        self.assertIs(ImprovementState.MEASURED, measured.state)
        self.assertTrue(measured.is_measured)
        self.assertIsNotNone(measured.outcome)

    def test_an_unapproved_proposal_cannot_be_measured(self):
        with self.assertRaises(ImprovementNotApprovedError):
            improvement_proposal().record_outcome(
                outcome=improvement_outcome()
            )

    def test_a_rejected_proposal_cannot_be_measured(self):
        rejected = improvement_proposal().reject(reason="not worth the change")

        with self.assertRaises(ImprovementNotApprovedError):
            rejected.record_outcome(outcome=improvement_outcome())

    def test_an_outcome_from_another_tenant_is_refused(self):
        foreign = improvement_outcome(
            tenant_id="client-other",
            metric=metric_definition(tenant_id="client-other"),
        )

        with self.assertRaises(ImprovementOutcomeSupportError):
            approved_improvement().record_outcome(outcome=foreign)

    def test_an_outcome_grounded_on_a_placeholder_measurement_is_refused(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementObservationError,
        )

        with self.assertRaises(ImprovementObservationError):
            improvement_outcome(
                after=measurement_record(
                    record_id="measure-after-3f",
                    value=8.0,
                    basis=MeasurementBasis.PLACEHOLDER,
                    sample_size=0,
                )
            )

    def test_a_measured_improvement_keeps_the_before_and_after_observation(self):
        measured = measured_improvement()

        before, after = measured.outcome.observations(
            baseline_id=measured.baseline.baseline_id
        )
        self.assertIs(ClaimKind.OBSERVATION, before.kind)
        self.assertIs(ClaimKind.OBSERVATION, after.kind)
        self.assertNotEqual(before.statement, after.statement)
        self.assertEqual(measured.baseline.baseline_id, before.baseline_id)
        self.assertEqual(measured.baseline.baseline_id, after.baseline_id)


class ImprovementOutcomeTests(unittest.TestCase):
    def test_an_outcome_requires_identity_tenant_summary_and_date(self):
        from redops.contexts.measurement.domain.value_objects import (
            ImprovementOutcome,
        )

        base = improvement_outcome()
        values = {
            "outcome_id": base.outcome_id,
            "tenant_id": base.tenant_id,
            "metric": base.metric,
            "before": base.before,
            "after": base.after,
            "measured_on": base.measured_on,
            "summary": base.summary,
        }
        for field in ("outcome_id", "tenant_id", "summary"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidImprovementOutcomeError):
                    ImprovementOutcome(**{**values, field: "  "})

    def test_the_before_and_after_must_share_a_tenant(self):
        foreign = metric_definition(
            metric_id="metric-foreign", tenant_id="client-other"
        )

        with self.assertRaises(InvalidImprovementOutcomeError):
            improvement_outcome(
                before=measurement_record(
                    metric=foreign,
                    tenant_id="client-other",
                    record_id="measure-before-3f",
                )
            )

    def test_the_before_and_after_must_attach_to_the_outcome_metric(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementObservationError,
        )

        with self.assertRaises(ImprovementObservationError):
            improvement_outcome(
                after=measurement_record(
                    metric=metric_definition(metric_id="metric-lead-volume"),
                    record_id="measure-after-3f",
                    value=8.0,
                )
            )

    def test_the_before_and_after_must_be_distinct_observations(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementObservationError,
        )

        shared = measurement_record(record_id="measure-before-3f", value=12.0)

        with self.assertRaises(ImprovementObservationError):
            improvement_outcome(before=shared, after=shared)

    def test_the_before_window_must_end_before_the_after_window_starts(self):
        with self.assertRaises(ImprovementObservationError):
            improvement_outcome(
                before=measurement_record(
                    record_id="measure-before-3f",
                    value=12.0,
                    window=MeasurementWindow(
                        start=date(2026, 9, 18), end=date(2026, 10, 1)
                    ),
                ),
                after=measurement_record(
                    record_id="measure-after-3f",
                    value=8.0,
                    window=MeasurementWindow(
                        start=date(2026, 9, 4), end=date(2026, 9, 17)
                    ),
                ),
            )

    def test_the_before_and_after_windows_cannot_overlap(self):
        with self.assertRaises(ImprovementObservationError):
            improvement_outcome(
                before=measurement_record(
                    record_id="measure-before-3f",
                    value=12.0,
                    window=MeasurementWindow(
                        start=date(2026, 9, 18), end=date(2026, 10, 1)
                    ),
                ),
                after=measurement_record(
                    record_id="measure-after-3f",
                    value=8.0,
                    window=MeasurementWindow(
                        start=date(2026, 9, 25), end=date(2026, 10, 8)
                    ),
                    recorded_on=date(2026, 10, 8),
                ),
            )

    def test_the_default_outcome_observes_after_the_before_window(self):
        outcome = improvement_outcome()

        self.assertLess(outcome.before.window.end, outcome.after.window.start)

    def test_a_placeholder_measurement_cannot_be_an_observation(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementObservationError,
        )

        with self.assertRaises(ImprovementObservationError):
            improvement_outcome(
                before=measurement_record(
                    record_id="measure-before-3f",
                    basis=MeasurementBasis.PLACEHOLDER,
                    sample_size=0,
                )
            )

    def test_the_observation_claims_project_to_typed_observations(self):
        outcome = improvement_outcome()

        before, after = outcome.observations(baseline_id="baseline-3f")

        self.assertIs(ClaimKind.OBSERVATION, before.kind)
        self.assertIs(ClaimKind.OBSERVATION, after.kind)
        self.assertEqual(outcome.metric.name, before.subject)
        self.assertEqual(outcome.metric.name, after.subject)
        self.assertEqual("outcome-3f:before", before.claim_id)
        self.assertIn("12.0", before.statement)

    def test_an_outcome_is_immutable(self):
        outcome = improvement_outcome()

        with self.assertRaises(FrozenInstanceError):
            outcome.summary = "tampered"


class ImprovementApprovalPrecedenceTests(unittest.TestCase):
    """An improvement's result cannot be read before its owner authorized it.

    SPEC.md section 4: "performance recommendations require evidence and owner
    approval before material changes", and only then is the change applied and its
    result read. The canon's optimization discipline (canon files 23 and 24: "I
    wait 10 days to see how it does"; "don't touch anything for 10 days") treats
    the result window as starting after the authorized change, so an after
    observation window that begins before the named owner's approval date is
    refused. The before window (the baseline period) may of course precede the
    approval.
    """

    def test_an_outcome_cannot_read_its_after_window_before_owner_approval(self):
        with self.assertRaises(ImprovementObservationWindowError):
            approved_improvement().record_outcome(
                outcome=improvement_outcome(
                    before=measurement_record(
                        record_id="measure-before-3f",
                        value=12.0,
                        window=MeasurementWindow(
                            start=date(2026, 9, 1), end=date(2026, 9, 14)
                        ),
                    ),
                    after=measurement_record(
                        record_id="measure-after-3f",
                        value=8.0,
                        window=MeasurementWindow(
                            start=date(2026, 9, 15), end=date(2026, 9, 20)
                        ),
                    ),
                )
            )

    def test_the_after_window_may_begin_on_the_approval_date(self):
        approved = improvement_proposal().approve(
            approval=improvement_approval(approved_on=date(2026, 10, 2))
        )

        measured = approved.record_outcome(
            outcome=improvement_outcome(
                before=measurement_record(
                    record_id="measure-before-3f",
                    value=12.0,
                    window=MeasurementWindow(
                        start=date(2026, 9, 18), end=date(2026, 10, 1)
                    ),
                ),
                after=measurement_record(
                    record_id="measure-after-3f",
                    value=8.0,
                    window=MeasurementWindow(
                        start=date(2026, 10, 2), end=date(2026, 10, 2)
                    ),
                ),
            )
        )

        self.assertTrue(measured.is_measured)

    def test_a_grounded_outcome_observes_after_its_approval_date(self):
        measured = measured_improvement()

        self.assertGreaterEqual(
            measured.outcome.after.window.start,
            measured.approval.approved_on,
        )


class ImprovementBaselineApprovalPrecedenceTests(unittest.TestCase):
    """An improvement cannot be authorized before its baseline was established.

    SPEC.md section 4, stage 10: an improvement is grounded on an established
    ``PerformanceBaseline`` and "performance recommendations require evidence and
    owner approval before material changes". The canon's optimization discipline
    (canon files 23 and 24: "you need a baseline of metrics" before optimizing;
    "I wait 10 days to see how it does" after authorizing a change) requires the
    baseline of metrics to exist before a change is authorized, so a named owner
    cannot approve an improvement on a date before the very baseline it optimizes
    was established. The improvement approval is otherwise only checked for owner
    authority, state and an established baseline, which leaves this cross-record
    temporal edge open.
    """

    def test_an_improvement_cannot_be_approved_before_its_baseline_was_established(
        self,
    ):
        proposal = improvement_proposal(baseline=established_baseline())

        with self.assertRaises(ImprovementApprovalPrecedenceError):
            proposal.approve(
                approval=improvement_approval(approved_on=date(2026, 10, 1))
            )

    def test_an_improvement_may_be_approved_the_day_its_baseline_was_established(
        self,
    ):
        approved = improvement_proposal(
            baseline=established_baseline()
        ).approve(
            approval=improvement_approval(approved_on=date(2026, 10, 2))
        )

        self.assertTrue(approved.is_approved)

    def test_a_grounded_improvement_is_approved_no_earlier_than_its_baseline(
        self,
    ):
        approved = approved_improvement()

        self.assertGreaterEqual(
            approved.approval.approved_on,
            approved.baseline.established_on,
        )


class ImprovementBeforeWindowPrecedenceTests(unittest.TestCase):
    """The before state must be observed before the change was authorized.

    SPEC.md section 4: "performance recommendations require evidence and owner
    approval before material changes", so the ``before`` measurement is a
    pre-change state and cannot be read from a period that extends past the
    authorization of the change. The canon's optimization discipline (canon files
    23 and 24: "you need a baseline of metrics" before optimizing; "I wait 10 days
    to see how it does" after authorizing a change) treats the before window as
    the established baseline period, so it must close on or before the named
    owner's approval date. The policy otherwise only compares the before window
    with the after window, which leaves this approval-versus-before edge open: a
    period observed after the change was authorized could still be recorded as the
    pre-change measurement.
    """

    def test_a_before_window_closing_after_owner_approval_is_refused(self):
        approved = improvement_proposal().approve(
            approval=improvement_approval(approved_on=date(2026, 10, 2))
        )

        with self.assertRaises(ImprovementBeforeWindowError):
            approved.record_outcome(
                outcome=improvement_outcome(
                    before=measurement_record(
                        record_id="measure-before-3f",
                        value=12.0,
                        window=MeasurementWindow(
                            start=date(2026, 10, 3), end=date(2026, 10, 5)
                        ),
                        recorded_on=date(2026, 10, 5),
                    ),
                    after=measurement_record(
                        record_id="measure-after-3f",
                        value=8.0,
                        window=MeasurementWindow(
                            start=date(2026, 10, 6), end=date(2026, 10, 6)
                        ),
                        recorded_on=date(2026, 10, 6),
                    ),
                    measured_on=date(2026, 10, 6),
                )
            )

    def test_the_before_window_may_close_on_the_approval_date(self):
        approved = improvement_proposal().approve(
            approval=improvement_approval(approved_on=date(2026, 10, 5))
        )

        measured = approved.record_outcome(
            outcome=improvement_outcome(
                before=measurement_record(
                    record_id="measure-before-3f",
                    value=12.0,
                    window=MeasurementWindow(
                        start=date(2026, 10, 3), end=date(2026, 10, 5)
                    ),
                    recorded_on=date(2026, 10, 5),
                ),
                after=measurement_record(
                    record_id="measure-after-3f",
                    value=8.0,
                    window=MeasurementWindow(
                        start=date(2026, 10, 6), end=date(2026, 10, 6)
                    ),
                    recorded_on=date(2026, 10, 6),
                ),
                measured_on=date(2026, 10, 6),
            )
        )

        self.assertTrue(measured.is_measured)

    def test_a_grounded_outcome_observes_before_on_or_before_approval(self):
        measured = measured_improvement()

        self.assertLessEqual(
            measured.outcome.before.window.end,
            measured.approval.approved_on,
        )


class ImprovementOutcomeSettlementTests(unittest.TestCase):
    """A result is read only once its own result window has closed.

    SPEC.md section 3 keys a ``MeasurementRecord`` by its window and keeps
    observations distinct from causal conclusions, and SPEC.md section 4, stage
    10 with Phase 5 read the observed result only after the optimization has run.
    The canon's optimization discipline (canon files 23 and 24: "I wait 10 days
    to see how it does"; "don't touch anything for 10 days") does not read a
    result until the window it is measured over has elapsed, so an outcome whose
    ``measured_on`` date falls before its after window has closed is refused:
    the result window is still open and the movement cannot yet be read.
    """

    def test_an_outcome_cannot_be_measured_before_its_after_window_closes(self):
        with self.assertRaises(ImprovementResultWindowOpenError):
            improvement_outcome(
                measured_on=date(2026, 10, 2),
                after=measurement_record(
                    record_id="measure-after-3f",
                    value=8.0,
                    window=MeasurementWindow(
                        start=date(2026, 10, 2), end=date(2026, 10, 5)
                    ),
                    recorded_on=date(2026, 10, 5),
                ),
            )

    def test_an_outcome_may_be_measured_on_the_day_its_after_window_closes(self):
        outcome = improvement_outcome(
            measured_on=date(2026, 10, 5),
            after=measurement_record(
                record_id="measure-after-3f",
                value=8.0,
                window=MeasurementWindow(
                    start=date(2026, 10, 2), end=date(2026, 10, 5)
                ),
                recorded_on=date(2026, 10, 5),
            ),
        )

        self.assertEqual(date(2026, 10, 5), outcome.after.window.end)
        self.assertEqual(date(2026, 10, 5), outcome.measured_on)

    def test_the_default_outcome_is_measured_after_its_after_window_closes(self):
        outcome = improvement_outcome()

        self.assertGreaterEqual(outcome.measured_on, outcome.after.window.end)


class ImprovementMetricGroundingTests(unittest.TestCase):
    """The improvement loop must run against a registered, versioned metric.

    SPEC.md section 3 keys a Measurement aggregate by its metric definition and
    keeps the stage 10 loop grounded on the cycle 93 registry, so an optimization
    cannot be proposed or measured against a free-text metric. Canon files 23 and
    24 make the typed funnel metric the lever an operator moves and warn against
    reading a rate until real metrics exist, so the proposal and its before/after
    observations pin the exact metric identity and version.
    """

    def test_a_proposal_is_pinned_to_a_registered_metric(self):
        proposal = improvement_proposal()

        self.assertEqual("metric-cost-per-lead", proposal.metric.metric_id)
        self.assertEqual(1, proposal.metric.version)

    def test_a_proposal_cannot_use_another_tenants_metric(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementMetricBoundaryError,
        )

        with self.assertRaises(ImprovementMetricBoundaryError):
            improvement_proposal(
                metric=metric_definition(
                    metric_id="metric-foreign", tenant_id="client-other"
                )
            )

    def test_a_proposal_subject_must_match_its_registered_metric(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementMetricError,
        )

        with self.assertRaises(ImprovementMetricError):
            improvement_proposal(subject="lead volume")

    def test_a_proposal_requires_a_registered_metric(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementMetricError,
        )

        with self.assertRaises(ImprovementMetricError):
            improvement_proposal(metric="cost per lead")

    def test_an_outcome_is_pinned_to_a_registered_metric(self):
        outcome = improvement_outcome()

        self.assertEqual("metric-cost-per-lead", outcome.metric.metric_id)
        self.assertEqual(1, outcome.metric.version)

    def test_an_outcome_records_must_attach_to_its_registered_metric(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementObservationError,
        )

        with self.assertRaises(ImprovementObservationError):
            improvement_outcome(
                after=measurement_record(
                    metric=metric_definition(version=2),
                    record_id="measure-after-3f",
                    value=8.0,
                )
            )

    def test_an_outcome_from_another_tenant_metric_is_refused(self):
        from redops.contexts.measurement.domain.errors import (
            InvalidImprovementOutcomeError,
        )

        foreign = metric_definition(
            metric_id="metric-foreign", tenant_id="client-other"
        )
        with self.assertRaises(InvalidImprovementOutcomeError):
            improvement_outcome(
                tenant_id=TENANT,
                metric=foreign,
                before=measurement_record(
                    metric=foreign,
                    tenant_id="client-other",
                    record_id="measure-before-3f",
                    value=12.0,
                ),
                after=measurement_record(
                    metric=foreign,
                    tenant_id="client-other",
                    record_id="measure-after-3f",
                    value=8.0,
                ),
            )

    def test_an_outcome_cannot_measure_against_a_different_metric(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementMetricMismatchError,
        )

        with self.assertRaises(ImprovementMetricMismatchError):
            approved_improvement().record_outcome(
                outcome=improvement_outcome(
                    metric=metric_definition(metric_id="metric-lead-volume")
                )
            )

    def test_an_outcome_cannot_measure_against_a_newer_metric_version(self):
        from redops.contexts.measurement.domain.errors import (
            ImprovementMetricMismatchError,
        )

        with self.assertRaises(ImprovementMetricMismatchError):
            approved_improvement().record_outcome(
                outcome=improvement_outcome(
                    metric=metric_definition(version=2)
                )
            )

    def test_a_measured_improvement_pins_the_approved_metric(self):
        measured = measured_improvement()

        self.assertEqual(
            measured.metric.metric_id, measured.outcome.metric.metric_id
        )
        self.assertEqual(measured.metric.version, measured.outcome.metric.version)


if __name__ == "__main__":
    unittest.main()
