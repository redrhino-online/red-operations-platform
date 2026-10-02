"""Behavioral tests for offer change impact discovery (pure domain, Commercial).

Rules under test come from SPEC.md sections 4 and 11:
- "Changing an approved upstream method emits an impact assessment: dependent
  offers ... are marked review required, with human owners and due dates"
  (SPEC.md section 4).
- "changing a method version identifies dependents" (SPEC.md section 11) must be
  satisfied by discovering real `OfferVersion.method_refs` rather than a
  caller-supplied list.
- Previous deployed releases stay historically identifiable (SPEC.md section 4).
"""

import unittest
from datetime import date

from redops.contexts.commercial.domain.entities import OfferVersion
from redops.contexts.commercial.domain.errors import InvalidOfferError
from redops.contexts.commercial.domain.policies import OfferChangeImpactPolicy
from redops.contexts.commercial.domain.value_objects import (
    MethodReference,
    OfferState,
)
from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.errors import MethodChangeImpactError
from redops.contexts.method.domain.value_objects import (
    ArtifactKind,
    SemanticVersion,
)

from ..method.fixtures import diagnostic_model, primary_currency

TODAY = date(2026, 10, 2)
DUE = date(2026, 10, 16)
USE = "3f pilot campaign"


def approved_method(version: SemanticVersion = SemanticVersion(1, 0, 0)) -> MethodVersion:
    return MethodVersion(
        method_id="method-3f",
        tenant_id="client-3f",
        parent_method="signature-solution",
        semantic_version=version,
        stages=("diagnose", "position", "model"),
        currency="qualified-referrals",
        claims=frozenset({"claim-1"}),
        primary_currency=primary_currency(),
        diagnostic_model=diagnostic_model(),
    ).approve(approved_by="client-authority", intended_use=USE, on=TODAY)


def offer(
    offer_id: str = "offer-1",
    *,
    method_id: str = "method-3f",
    version: SemanticVersion = SemanticVersion(1, 0, 0),
    intended_use: str = USE,
    tenant_id: str = "client-3f",
    owner: str = "offer-owner",
    state: OfferState = OfferState.PRODUCTION_READY,
) -> OfferVersion:
    return OfferVersion(
        offer_id=offer_id,
        tenant_id=tenant_id,
        audience="owner-operators",
        promise="twice the qualified referrals",
        eligibility="service businesses with a proven offer",
        price_hypothesis="USD 7,500",
        method_refs=(
            MethodReference(
                method_id=method_id,
                version=version,
                intended_use=intended_use,
            ),
        ),
        owner=owner,
        state=state,
    )


def revised(previous: MethodVersion) -> MethodVersion:
    return previous.revised(semantic_version=SemanticVersion(1, 1, 0))


class OfferChangeImpactTests(unittest.TestCase):
    def test_a_method_change_marks_its_dependent_offers_review_required(self):
        previous = approved_method()
        current = revised(previous)

        assessment = OfferChangeImpactPolicy().assess(
            previous, current, [offer()], due_on=DUE
        )

        self.assertEqual(("offer-1",), assessment.review_required_offer_ids)
        self.assertIs(OfferState.REVIEW_REQUIRED, assessment.offers[0].state)
        self.assertFalse(assessment.offers[0].is_production_ready)

    def test_only_offers_pinned_to_the_changed_version_are_discovered(self):
        previous = approved_method()
        current = revised(previous)
        dependents = [offer("offer-1")]
        others = [
            offer("offer-2", method_id="method-other"),
            offer("offer-3", version=SemanticVersion(0, 9, 0)),
            offer("offer-4", intended_use="another engagement"),
            offer("offer-5", tenant_id="client-other"),
        ]

        assessment = OfferChangeImpactPolicy().assess(
            previous, current, dependents + others, due_on=DUE
        )

        self.assertEqual(("offer-1",), assessment.review_required_offer_ids)

    def test_a_terminal_offer_is_not_revived_by_a_method_change(self):
        previous = approved_method()
        current = revised(previous)

        assessment = OfferChangeImpactPolicy().assess(
            previous, current, [offer(state=OfferState.SUPERSEDED)], due_on=DUE
        )

        self.assertEqual((), assessment.offers)

    def test_every_discovered_offer_is_an_owned_review_requirement(self):
        previous = approved_method()
        current = revised(previous)

        assessment = OfferChangeImpactPolicy().assess(
            previous,
            current,
            [offer("offer-1", owner="alice"), offer("offer-2", owner="bob")],
            due_on=DUE,
        )

        self.assertEqual(
            {"offer-1", "offer-2"}, set(assessment.review_required_offer_ids)
        )
        for requirement in assessment.impact.requirements:
            self.assertIs(ArtifactKind.OFFER, requirement.artifact.kind)
            self.assertEqual(DUE, requirement.due_on)
            self.assertTrue(requirement.artifact.owner)

    def test_a_change_to_an_unapproved_method_emits_no_assessment(self):
        unapproved = MethodVersion(
            method_id="method-3f",
            tenant_id="client-3f",
            parent_method="signature-solution",
            semantic_version=SemanticVersion(1, 0, 0),
            stages=("diagnose",),
            currency="qualified-referrals",
            claims=frozenset(),
        )
        current = unapproved.revised(semantic_version=SemanticVersion(1, 1, 0))

        with self.assertRaises(MethodChangeImpactError):
            OfferChangeImpactPolicy().assess(
                unapproved, current, [offer()], due_on=DUE
            )

    def test_the_previous_approved_method_stays_identifiable(self):
        previous = approved_method()
        current = revised(previous)

        OfferChangeImpactPolicy().assess(previous, current, [offer()], due_on=DUE)

        self.assertTrue(previous.is_approved)
        self.assertEqual(SemanticVersion(1, 0, 0), previous.approval.version)
        self.assertFalse(current.is_approved)


class OfferOwnerTests(unittest.TestCase):
    def test_an_offer_requires_an_accountable_owner(self):
        with self.assertRaises(InvalidOfferError):
            offer(owner="  ")


if __name__ == "__main__":
    unittest.main()
