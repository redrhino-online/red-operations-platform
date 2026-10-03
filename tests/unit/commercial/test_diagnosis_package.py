"""Behavioral tests for the stage 1 diagnosis asset package (Commercial domain).

Rules under test come from SPEC.md sections 3 and 4 and the reference model
canon (SPEC.md section 12.3 maps stage 1 "Diagnose" to canon files 02, 03 and
04). The stage 1 template enumerates eleven required asset kinds -- avatar
profile, pains, goals, consequences of inaction, awareness map, audience reach
estimate, target market match, customer evidence, voice notes, business snapshot
and offer and funnel audit -- while the Commercial context reviews them as five
rich value objects. This package is the bridge: it projects the reviewed values
onto the eleven canonical kinds as exact ``StageAssetVersion`` evidence so a
stage 1 gate can pin one exact version per kind.

- A passing gate pins the exact evidence and intended downstream use, so the
  package carries a positive version per reviewed asset and refuses a versionless
  one.
- Every child resource belongs to exactly one client, so a cross-tenant
  diagnosis value is refused rather than pinned.
- The canonical required kinds are owned by the pipeline template, not by the
  caller, so the package's kind set must match the stage 1 template exactly.

The canon groups the avatar's pains, goals, consequences and why into one Avatar
Goals Grid (canon 04); the SPEC stage 1 package enumerates them as separate
required items, so the package exposes them as separate exact-version kinds
while the avatar value carries their content. These tests never invent a named
client approver or a concrete authority role.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.commercial.domain.errors import (
    DiagnosisTenantBoundaryError,
    InvalidDiagnosisPackageError,
)
from redops.contexts.commercial.domain.value_objects import (
    CANONICAL_DIAGNOSIS_KINDS,
    AudienceDefinition,
    AudienceReachEstimate,
    AvatarProfile,
    BusinessSnapshot,
    DiagnosisPackage,
    InterestKind,
    InterestSignal,
    MarketAwarenessLevel,
    MarketAwarenessMap,
    OfferFunnelAudit,
    ResearchPlatform,
    TargetMarketCandidate,
    TargetMarketMatchmaker,
)
from redops.contexts.governance.domain.entities import StageGate
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template

TENANT = "client-3f"
OTHER_TENANT = "client-other"


def avatar(*, tenant_id: str = TENANT) -> AvatarProfile:
    return AvatarProfile(
        avatar_id="avatar-3f",
        tenant_id=tenant_id,
        name="Owner-operator of a small service firm",
        demographics="35-50, runs a two to five person local service firm",
        psychographics="proud of craft, skeptical of marketing, time poor",
        pains=("feast and famine pipeline",),
        goals=("predictable qualified demand",),
        consequences_of_inaction=("hires then lays off as work dries up",),
        awareness="problem aware, not solution aware",
        customer_evidence_claim_ids=("claim-voice-1",),
        voice_notes=("I cannot plan payroll when the phone is quiet",),
    )


def snapshot(*, tenant_id: str = TENANT) -> BusinessSnapshot:
    return BusinessSnapshot(
        snapshot_id="snapshot-3f",
        tenant_id=tenant_id,
        business_model="project based service work billed hourly",
        current_offers=("hourly support retainer",),
        lead_sources=("referrals",),
        constraints=("two delivery people, no marketing owner",),
        narrative="Steady referrals but no predictable pipeline between projects",
        evidence_claim_ids=("claim-offer-1",),
    )


def audit(*, tenant_id: str = TENANT) -> OfferFunnelAudit:
    return OfferFunnelAudit(
        audit_id="audit-3f",
        tenant_id=tenant_id,
        offer_findings=("the retainer has no stated outcome",),
        funnel_steps=("referral", "call", "quote", "project"),
        conversion_evidence=("quotes are tracked in a spreadsheet",),
        gaps=("no qualification step before the call",),
        narrative="The funnel has no owner between referral and quote",
        evidence_claim_ids=("claim-offer-1",),
    )


def awareness_map(*, tenant_id: str = TENANT) -> MarketAwarenessMap:
    return MarketAwarenessMap(
        map_id="awareness-3f",
        tenant_id=tenant_id,
        primary_level=MarketAwarenessLevel.PROBLEM_AWARE,
        research_evidence=("reviews name the unpredictable pipeline",),
        message_requirements=("lead with the predictable pipeline outcome",),
        retarget_level=MarketAwarenessLevel.SOLUTION_AWARE,
    )


def reach(*, tenant_id: str = TENANT) -> AudienceReachEstimate:
    return AudienceReachEstimate(
        estimate_id="reach-3f",
        tenant_id=tenant_id,
        owner="red-owner",
        platform=ResearchPlatform.FACEBOOK_AUDIENCE_INSIGHTS,
        audience=AudienceDefinition(
            location="United States",
            age="35-50",
            gender="all",
            interests=(
                InterestSignal(
                    kind=InterestKind.EXPERT,
                    value="small service firm coach",
                ),
            ),
        ),
        estimated_reach=180000,
        source_note="Facebook Audience Insights sizing on 2026-10-03",
        captured_on=date(2026, 10, 3),
    )


def matchmaker(*, tenant_id: str = TENANT) -> TargetMarketMatchmaker:
    return TargetMarketMatchmaker(
        matchmaker_id="match-3f",
        tenant_id=tenant_id,
        candidates=(
            TargetMarketCandidate(
                market_id="market-referrals",
                name="Referral-starved service business owners",
                passion="we have run this play inside the trade",
                problem="unpredictable referral flow",
                profit="they already spend on lead generation",
                reachability="active in two owner-operator communities",
                pathway="from a referral drought to a referral partner engine",
            ),
            TargetMarketCandidate(
                market_id="market-coaches",
                name="New executive coaches",
                passion="we coach this transition",
                problem="no repeatable client acquisition",
                profit="they invest in their practice",
                reachability="active in coach communities",
                pathway="from no pipeline to a repeatable acquisition engine",
            ),
        ),
        selected_market_id="market-referrals",
        awareness_map=awareness_map(tenant_id=tenant_id),
    )


def package(**overrides) -> DiagnosisPackage:
    values = {
        "package_id": "diagnosis-3f",
        "tenant_id": TENANT,
        "avatar": avatar(),
        "avatar_version": 1,
        "business_snapshot": snapshot(),
        "business_snapshot_version": 1,
        "offer_funnel_audit": audit(),
        "offer_funnel_audit_version": 1,
        "awareness_map": awareness_map(),
        "awareness_map_version": 1,
        "audience_reach_estimate": reach(),
        "audience_reach_estimate_version": 1,
        "target_market_match": matchmaker(),
        "target_market_match_version": 1,
    }
    values.update(overrides)
    return DiagnosisPackage(**values)


class DiagnosisPackageKindTests(unittest.TestCase):
    def test_the_canonical_kinds_match_the_stage_one_template(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(1)

        self.assertEqual(template_kinds, frozenset(CANONICAL_DIAGNOSIS_KINDS))

    def test_the_package_covers_every_canonical_kind(self):
        self.assertEqual(
            frozenset(CANONICAL_DIAGNOSIS_KINDS),
            frozenset(ref.asset_id for ref in _pins(package())),
        )
        self.assertEqual((), package().missing_kinds())


def _pins(value: DiagnosisPackage):
    return tuple(
        asset.pin(tenant_id=value.tenant_id)
        for asset in value.stage_asset_versions()
    )


class DiagnosisPackageProjectionTests(unittest.TestCase):
    def test_the_projection_pins_the_exact_version_each_reviewed_asset_carries(self):
        value = package(
            avatar_version=2,
            business_snapshot_version=3,
            offer_funnel_audit_version=4,
            awareness_map_version=5,
            audience_reach_estimate_version=6,
            target_market_match_version=7,
        )

        versions = {
            ref.asset_id: ref.version for ref in _pins(value)
        }

        for kind in (
            "avatar-profile",
            "pains",
            "goals",
            "consequences-of-inaction",
            "customer-evidence",
            "voice-notes",
        ):
            self.assertEqual(2, versions[kind], kind)
        self.assertEqual(5, versions["awareness-map"])
        self.assertEqual(3, versions["business-snapshot"])
        self.assertEqual(4, versions["offer-funnel-audit"])
        self.assertEqual(6, versions["audience-reach-estimate"])
        self.assertEqual(7, versions["target-market-match"])

    def test_the_target_market_match_kind_is_pinned_from_the_typed_match(self):
        value = package(target_market_match_version=7)

        by_kind = {ref.asset_id: ref for ref in _pins(value)}
        source = {
            asset.kind: asset for asset in value.stage_asset_versions()
        }

        self.assertEqual(7, by_kind["target-market-match"].version)
        self.assertEqual("match-3f", source["target-market-match"].asset_id)

    def test_the_audience_reach_kind_is_pinned_from_the_typed_estimate(self):
        value = package(audience_reach_estimate_version=7)

        by_kind = {ref.asset_id: ref for ref in _pins(value)}
        source = {
            asset.kind: asset for asset in value.stage_asset_versions()
        }

        self.assertEqual(7, by_kind["audience-reach-estimate"].version)
        self.assertEqual("reach-3f", source["audience-reach-estimate"].asset_id)

    def test_the_awareness_map_kind_is_pinned_from_the_typed_map(self):
        value = package(awareness_map_version=7)

        by_kind = {ref.asset_id: ref for ref in _pins(value)}
        source = {
            asset.kind: asset for asset in value.stage_asset_versions()
        }

        self.assertEqual(7, by_kind["awareness-map"].version)
        self.assertEqual("awareness-3f", source["awareness-map"].asset_id)

    def test_the_projected_assets_assemble_a_canonical_stage_one_gate(self):
        gate = StageGate.from_assets(
            stage_zero_to_ten_template(),
            1,
            tenant_id=TENANT,
            assets=package(
                avatar_version=2,
                business_snapshot_version=3,
                offer_funnel_audit_version=4,
            ).stage_asset_versions(),
        )

        self.assertEqual(1, gate.stage_number)
        self.assertEqual(
            frozenset(CANONICAL_DIAGNOSIS_KINDS),
            frozenset(ref.asset_id for ref in gate.required_assets),
        )
        self.assertEqual("Avatar Locked", gate.checkpoint)


class DiagnosisPackageRejectionTests(unittest.TestCase):
    def test_a_missing_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidDiagnosisPackageError):
                    package(**override)

    def test_a_versionless_or_non_positive_version_is_refused(self):
        for override in (
            {"avatar_version": 0},
            {"business_snapshot_version": -1},
            {"offer_funnel_audit_version": 0},
            {"awareness_map_version": 0},
            {"audience_reach_estimate_version": 0},
            {"target_market_match_version": 0},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidDiagnosisPackageError):
                    package(**override)

    def test_a_cross_tenant_diagnosis_asset_is_refused(self):
        with self.assertRaises(DiagnosisTenantBoundaryError):
            package(avatar=avatar(tenant_id=OTHER_TENANT))
        with self.assertRaises(DiagnosisTenantBoundaryError):
            package(business_snapshot=snapshot(tenant_id=OTHER_TENANT))
        with self.assertRaises(DiagnosisTenantBoundaryError):
            package(offer_funnel_audit=audit(tenant_id=OTHER_TENANT))
        with self.assertRaises(DiagnosisTenantBoundaryError):
            package(awareness_map=awareness_map(tenant_id=OTHER_TENANT))
        with self.assertRaises(DiagnosisTenantBoundaryError):
            package(
                audience_reach_estimate=reach(tenant_id=OTHER_TENANT)
            )
        with self.assertRaises(DiagnosisTenantBoundaryError):
            package(
                target_market_match=matchmaker(tenant_id=OTHER_TENANT)
            )

    def test_the_package_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            package().avatar_version = 9


if __name__ == "__main__":
    unittest.main()
