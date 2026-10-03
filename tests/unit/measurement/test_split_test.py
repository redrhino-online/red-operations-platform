"""Behavioral tests for stage 10 split-test logging (Measurement domain).

Rules under test come from SPEC.md section 4, stage 10 ("performance
recommendations require evidence and owner approval before material changes",
with the observed movement kept distinct from a causal conclusion) shaped by the
canon's split-test discipline (canon files 22, 23 and 24):

- Split testing starts only once a baseline of metrics exists and the staged
  optimization has been owner-approved (canon file 24: "You shouldn't do it in
  the beginning because you need a baseline of metrics").
- The test changes exactly one variable at a time (canon file 24: "I'm not going
  to change this headline and the image and the button text. Why? Because how do I
  know what the hell worked?").
- The two ways to run it are pausing and cloning, or running both together
  (canon file 24: "I pause the first ad, clone it... Or if I have the budget, I
  just run them both together. That's only two ways you could possibly do it").
- The change is logged before the result is read, and the result is read only
  after its window closes (canon file 24: "I wait 10 days to see how it does").
- The log records what changed; it is not the measured movement and not a causal
  conclusion.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.measurement.domain.errors import (
    InvalidSplitTestError,
    SplitTestChangeError,
    SplitTestDependencyError,
    SplitTestLeverError,
    SplitTestObservationError,
    SplitTestTenantBoundaryError,
    SplitTestVariableError,
    SplitTestWindowOpenError,
)
from redops.contexts.measurement.domain.value_objects import (
    MeasurementWindow,
    SplitTest,
    SplitTestChange,
    SplitTestMode,
)

from .fixtures import approved_improvement, improvement_proposal

TENANT = "client-3f"
WINDOW = MeasurementWindow(start=date(2026, 10, 3), end=date(2026, 10, 12))


def headline_change(**overrides) -> SplitTestChange:
    values = {
        "variable": "landing page headline",
        "from_value": "Grow your consulting business",
        "to_value": "Only for established consultants doing 10k a month",
    }
    values.update(overrides)
    return SplitTestChange(**values)


def split_test(**overrides) -> SplitTest:
    values = {
        "test_id": "split-3f",
        "tenant_id": TENANT,
        "optimization": approved_improvement(),
        "changes": (headline_change(),),
        "mode": SplitTestMode.PAUSE_AND_CLONE,
        "window": WINDOW,
        "read_on": date(2026, 10, 12),
        "rationale": "test one headline against the observed baseline",
    }
    values.update(overrides)
    return SplitTest(**values)


class SplitTestChangeTests(unittest.TestCase):
    def test_a_change_names_one_variable_and_its_before_and_after(self):
        change = headline_change()

        self.assertEqual("landing page headline", change.variable)
        self.assertNotEqual(change.from_value, change.to_value)

    def test_a_change_requires_a_variable_and_both_values(self):
        for field in ("variable", "from_value", "to_value"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidSplitTestError):
                    headline_change(**{field: "  "})

    def test_a_change_must_actually_change_something(self):
        with self.assertRaises(SplitTestChangeError):
            headline_change(to_value="Grow your consulting business")

    def test_a_change_is_immutable(self):
        change = headline_change()

        with self.assertRaises(FrozenInstanceError):
            change.to_value = "other"


class SplitTestTests(unittest.TestCase):
    def test_a_split_test_logs_the_single_changed_variable(self):
        test = split_test()

        self.assertEqual(1, len(test.changes))
        self.assertEqual("landing page headline", test.variable)
        self.assertIs(SplitTestMode.PAUSE_AND_CLONE, test.mode)

    def test_both_canon_modes_are_available(self):
        for mode in (SplitTestMode.PAUSE_AND_CLONE, SplitTestMode.RUN_CONCURRENT):
            with self.subTest(mode=mode):
                self.assertIs(mode, split_test(mode=mode).mode)

    def test_changing_more_than_one_variable_is_refused(self):
        with self.assertRaises(SplitTestVariableError):
            split_test(
                changes=(
                    headline_change(),
                    headline_change(
                        variable="landing page image", to_value="new image"
                    ),
                )
            )

    def test_changing_no_variable_is_refused(self):
        with self.assertRaises(SplitTestVariableError):
            split_test(changes=())

    def test_the_changed_variable_must_be_the_approved_optimization_lever(self):
        with self.assertRaises(SplitTestLeverError):
            split_test(
                changes=(headline_change(variable="landing page image"),)
            )

    def test_split_testing_needs_an_owner_approved_optimization(self):
        with self.assertRaises(SplitTestDependencyError):
            split_test(optimization=improvement_proposal())

    def test_the_result_is_read_only_after_the_test_window_closes(self):
        with self.assertRaises(SplitTestWindowOpenError):
            split_test(read_on=date(2026, 10, 11))

    def test_a_split_test_is_never_an_observed_result(self):
        test = split_test()

        self.assertTrue(test.is_split_test)
        with self.assertRaises(SplitTestObservationError):
            test.as_observation(claim_id="claim-split")

    def test_a_split_test_cannot_cross_a_tenant_boundary(self):
        with self.assertRaises(SplitTestTenantBoundaryError):
            split_test(tenant_id="other-client")

    def test_a_split_test_requires_its_identification_fields(self):
        for field in ("test_id", "tenant_id", "rationale"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidSplitTestError):
                    split_test(**{field: "  "})

    def test_a_split_test_is_immutable(self):
        test = split_test()

        with self.assertRaises(FrozenInstanceError):
            test.read_on = date(2026, 10, 20)


if __name__ == "__main__":
    unittest.main()
