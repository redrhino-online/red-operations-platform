"""Behavioral tests for method change impact assessment (pure domain, Method).

Rules under test come from SPEC.md sections 4 and 11:
- "Changing an approved upstream method emits an impact assessment: dependent
  offers, briefs, assets, journeys, and claims are marked review required, with
  human owners and due dates" (SPEC.md section 4).
- "changing a method version identifies dependents" (SPEC.md section 11).
- Previous deployed releases stay historically identifiable (SPEC.md section 4).
"""

import unittest
from datetime import date

from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.errors import MethodChangeImpactError
from redops.contexts.method.domain.policies import MethodChangeImpactPolicy
from redops.contexts.method.domain.value_objects import (
    ArtifactKind,
    ChangeSeverity,
    DependentArtifact,
    SemanticVersion,
)

TODAY = date(2026, 10, 2)
DUE = date(2026, 10, 16)


def approved_method(version: SemanticVersion = SemanticVersion(1, 0, 0)) -> MethodVersion:
    return MethodVersion(
        method_id="method-3f",
        tenant_id="client-3f",
        parent_method="signature-solution",
        semantic_version=version,
        stages=("diagnose", "position", "model"),
        currency="qualified-referrals",
        claims=frozenset({"claim-1"}),
    ).approve(
        approved_by="client-authority",
        intended_use="3f pilot campaign",
        on=TODAY,
    )


def dependents() -> tuple[DependentArtifact, ...]:
    return (
        DependentArtifact("offer-1", ArtifactKind.OFFER, "offer-owner"),
        DependentArtifact("brief-1", ArtifactKind.BRIEF, "production-owner"),
        DependentArtifact("asset-aa-1", ArtifactKind.ASSET, "asset-owner"),
        DependentArtifact("journey-1", ArtifactKind.JOURNEY, "journey-owner"),
        DependentArtifact("claim-1", ArtifactKind.CLAIM, "knowledge-owner"),
    )


class MethodChangeImpactTests(unittest.TestCase):
    def test_changing_an_approved_method_marks_all_dependents_review_required(self):
        previous = approved_method(SemanticVersion(1, 0, 0))
        current = previous.revised(
            semantic_version=SemanticVersion(1, 1, 0),
            currency="qualified-referrals-v2",
        )

        assessment = MethodChangeImpactPolicy().assess(
            previous, current, dependents(), due_on=DUE
        )

        self.assertEqual("method-3f", assessment.method_id)
        self.assertEqual(SemanticVersion(1, 0, 0), assessment.previous_version)
        self.assertEqual(SemanticVersion(1, 1, 0), assessment.new_version)
        self.assertEqual(5, len(assessment.requirements))
        self.assertEqual(
            {
                ArtifactKind.OFFER,
                ArtifactKind.BRIEF,
                ArtifactKind.ASSET,
                ArtifactKind.JOURNEY,
                ArtifactKind.CLAIM,
            },
            {requirement.artifact.kind for requirement in assessment.requirements},
        )

    def test_every_review_requirement_names_a_human_owner_and_due_date(self):
        previous = approved_method(SemanticVersion(1, 0, 0))
        current = previous.revised(semantic_version=SemanticVersion(1, 1, 0))

        assessment = MethodChangeImpactPolicy().assess(
            previous, current, dependents(), due_on=DUE
        )

        for requirement in assessment.requirements:
            self.assertTrue(requirement.artifact.owner)
            self.assertEqual(DUE, requirement.due_on)
            self.assertTrue(requirement.reason)

    def test_a_change_to_an_unapproved_method_emits_no_assessment(self):
        previous = MethodVersion(
            method_id="method-3f",
            tenant_id="client-3f",
            parent_method="signature-solution",
            semantic_version=SemanticVersion(1, 0, 0),
            stages=("diagnose",),
            currency="qualified-referrals",
            claims=frozenset(),
        )
        current = previous.revised(semantic_version=SemanticVersion(1, 1, 0))

        with self.assertRaises(MethodChangeImpactError):
            MethodChangeImpactPolicy().assess(
                previous, current, dependents(), due_on=DUE
            )

    def test_an_identical_version_emits_no_assessment(self):
        previous = approved_method(SemanticVersion(1, 0, 0))

        with self.assertRaises(MethodChangeImpactError):
            MethodChangeImpactPolicy().assess(
                previous, previous, dependents(), due_on=DUE
            )

    def test_a_patch_change_is_classified_editorial(self):
        previous = approved_method(SemanticVersion(1, 0, 0))
        current = previous.revised(semantic_version=SemanticVersion(1, 0, 1))

        assessment = MethodChangeImpactPolicy().assess(
            previous, current, dependents(), due_on=DUE
        )

        self.assertIs(ChangeSeverity.EDITORIAL, assessment.severity)

    def test_a_minor_change_is_classified_substantive(self):
        previous = approved_method(SemanticVersion(1, 0, 0))
        current = previous.revised(semantic_version=SemanticVersion(1, 1, 0))

        assessment = MethodChangeImpactPolicy().assess(
            previous, current, dependents(), due_on=DUE
        )

        self.assertIs(ChangeSeverity.SUBSTANTIVE, assessment.severity)

    def test_the_previous_approved_version_remains_identifiable(self):
        previous = approved_method(SemanticVersion(1, 0, 0))
        current = previous.revised(semantic_version=SemanticVersion(2, 0, 0))

        MethodChangeImpactPolicy().assess(previous, current, dependents(), due_on=DUE)

        self.assertTrue(previous.is_approved)
        self.assertEqual(SemanticVersion(1, 0, 0), previous.approval.version)
        self.assertFalse(current.is_approved)

    def test_an_assessment_with_no_dependents_is_still_recorded(self):
        previous = approved_method(SemanticVersion(1, 0, 0))
        current = previous.revised(semantic_version=SemanticVersion(1, 1, 0))

        assessment = MethodChangeImpactPolicy().assess(previous, current, ())

        self.assertEqual((), assessment.requirements)
        self.assertIs(ChangeSeverity.SUBSTANTIVE, assessment.severity)

    def test_change_impact_cannot_cross_a_tenant_boundary(self):
        previous = approved_method(SemanticVersion(1, 0, 0))
        foreign = MethodVersion(
            method_id="method-3f",
            tenant_id="client-other",
            parent_method="signature-solution",
            semantic_version=SemanticVersion(1, 1, 0),
            stages=previous.stages,
            currency=previous.currency,
            claims=previous.claims,
        )

        with self.assertRaises(MethodChangeImpactError):
            MethodChangeImpactPolicy().assess(previous, foreign, dependents(), due_on=DUE)


if __name__ == "__main__":
    unittest.main()
