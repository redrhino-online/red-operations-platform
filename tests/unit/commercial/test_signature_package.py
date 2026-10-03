"""Behavioral tests for the stage 4 "IP Architecture Locked" asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 4 "Package IP"
requires the asset package "transformation map, process inventory, three phases,
nine steps, named stages, starting and final states, inputs, actions, outputs,
narrative and visual", and its checkpoint is "IP Architecture Locked": "the
transformation is coherent and explainable without listing every tactic". The
reference model canon that informs this stage is files 09 and 10 (SPEC.md section
12.3): the Signature Solution core training and examples require a clear currency,
three main phases and nine clear steps from point A to point B, each named stage
carrying its own from/to transformation and why it matters, titled from the
million dollar message.

Like the stage 1 ``DiagnosisPackage`` (cycle 69), stage 2 ``CurrencyPackage``
(cycle 71) and stage 3 ``DiagnosticPackage`` (cycle 73) bridges, this package
projects the reviewed stage 4 ``SignatureSolution`` onto the twelve canonical
stage 4 asset kinds as exact ``StageAssetVersion`` evidence so a canonical gate
can be assembled. It refuses a blank identity, a versionless solution or a
cross-tenant solution rather than silently pinning inexact or foreign evidence.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidSignaturePackageError,
    SignatureTenantBoundaryError,
)
from redops.contexts.commercial.domain.value_objects import (
    CANONICAL_SIGNATURE_KINDS,
    SignaturePackage,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.method.domain.entities import SignatureSolution
from redops.contexts.method.domain.transformations import (
    THIRTEEN_TRANSFORMATIONS_KIND,
    ThirteenTransformations,
    Transformation,
    TransformationScope,
)
from redops.contexts.method.domain.value_objects import (
    SignatureStep,
    TransformationPhase,
)

TENANT = "client-3f"
OTHER_TENANT = "client-other"


def step(
    step_id: str,
    name: str,
    starting_state: str,
    final_state: str,
    tenant_id: str = TENANT,
) -> SignatureStep:
    return SignatureStep(
        step_id=step_id,
        tenant_id=tenant_id,
        name=name,
        starting_state=starting_state,
        final_state=final_state,
        inputs=(f"{name} inputs",),
        actions=(f"{name} actions",),
        outputs=(f"{name} outputs",),
    )


def nine_step_phases(tenant_id: str = TENANT) -> tuple[TransformationPhase, ...]:
    return (
        TransformationPhase(
            phase_id="phase-1",
            tenant_id=tenant_id,
            name="Diagnose and Position",
            steps=(
                step("step-1", "Diagnose", "chaotic", "diagnosed", tenant_id),
                step("step-2", "Position", "diagnosed", "positioned", tenant_id),
                step("step-3", "Model", "positioned", "modeled", tenant_id),
            ),
        ),
        TransformationPhase(
            phase_id="phase-2",
            tenant_id=tenant_id,
            name="Package and Productize",
            steps=(
                step("step-4", "Package IP", "modeled", "packaged", tenant_id),
                step("step-5", "Productize", "packaged", "productized", tenant_id),
                step("step-6", "Message", "productized", "messaged", tenant_id),
            ),
        ),
        TransformationPhase(
            phase_id="phase-3",
            tenant_id=tenant_id,
            name="Produce and Launch",
            steps=(
                step("step-7", "Produce", "messaged", "produced", tenant_id),
                step("step-8", "Integrate", "produced", "integrated", tenant_id),
                step("step-9", "Launch", "integrated", "launched", tenant_id),
            ),
        ),
    )


def solution(tenant_id: str = TENANT) -> SignatureSolution:
    return SignatureSolution(
        solution_id="solution-3f",
        tenant_id=tenant_id,
        transformation_map="from chaotic delivery to a launched campaign",
        process_inventory=("diagnose", "position", "model", "package"),
        phases=nine_step_phases(tenant_id),
        starting_state="chaotic",
        final_state="launched",
        narrative=(
            "the client moves from unpredictable work to a repeatable growth "
            "system"
        ),
        visual="asset://transformations/3f-map.png",
    )


def transformations(sol: SignatureSolution) -> ThirteenTransformations:
    return ThirteenTransformations(
        transformations_id="transformations-3f",
        tenant_id=sol.tenant_id,
        million_dollar_message=(
            "from chaotic delivery to a launched campaign"
        ),
        solution=sol,
        overall=Transformation(
            transformation_id="transformations-3f-overall",
            tenant_id=sol.tenant_id,
            scope=TransformationScope.OVERALL,
            scope_id=sol.solution_id,
            title="from chaotic delivery to a launched campaign",
            from_state=sol.starting_state,
            to_state=sol.final_state,
        ),
        phase_transformations=tuple(
            Transformation(
                transformation_id=f"transformations-3f-{phase.phase_id}",
                tenant_id=sol.tenant_id,
                scope=TransformationScope.PHASE,
                scope_id=phase.phase_id,
                title=phase.name,
                from_state=phase.steps[0].starting_state,
                to_state=phase.steps[-1].final_state,
            )
            for phase in sol.phases
        ),
        step_transformations=tuple(
            Transformation(
                transformation_id=f"transformations-3f-{step.step_id}",
                tenant_id=sol.tenant_id,
                scope=TransformationScope.STEP,
                scope_id=step.step_id,
                title=step.name,
                from_state=step.starting_state,
                to_state=step.final_state,
            )
            for step in sol.steps
        ),
    )


def package(**overrides) -> SignaturePackage:
    sol = overrides.get("solution", solution())
    values = {
        "package_id": "signature-3f",
        "tenant_id": TENANT,
        "solution": sol,
        "solution_version": 1,
        "transformations": transformations(sol),
        "transformations_version": 1,
    }
    values.update(overrides)
    return SignaturePackage(**values)


class SignaturePackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_canonical_stage_four_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_SIGNATURE_KINDS), kinds)
        self.assertEqual(13, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_four_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(4)

        self.assertEqual(template_kinds, frozenset(CANONICAL_SIGNATURE_KINDS))

    def test_every_kind_pins_the_reviewed_asset_at_its_exact_version(self):
        assets = package(
            solution_version=5, transformations_version=5
        ).stage_asset_versions()

        self.assertEqual(13, len(assets))
        for asset in assets:
            self.assertEqual(5, asset.version)

    def test_each_solution_kind_pins_the_reviewed_solution_identity(self):
        assets = package().stage_asset_versions()

        for asset in assets:
            if asset.kind == THIRTEEN_TRANSFORMATIONS_KIND:
                continue
            self.assertEqual("solution-3f", asset.asset_id)

    def test_the_thirteen_transformations_kind_pins_its_own_identity(self):
        assets = {
            asset.kind: asset for asset in package().stage_asset_versions()
        }

        asset = assets[THIRTEEN_TRANSFORMATIONS_KIND]
        self.assertEqual("transformations-3f", asset.asset_id)

    def test_the_projected_evidence_is_tenant_scoped(self):
        for asset in package().stage_asset_versions():
            self.assertEqual(TENANT, asset.tenant_id)

    def test_a_complete_package_reports_no_missing_kinds(self):
        value = package()

        self.assertTrue(value.is_complete)
        self.assertEqual((), value.missing_kinds())

    def test_the_package_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            package().package_id = "tampered"


class SignaturePackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_solution_is_refused(self):
        with self.assertRaises(SignatureTenantBoundaryError):
            package(solution=solution(tenant_id=OTHER_TENANT))

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidSignaturePackageError):
                    package(**override)

    def test_a_versionless_reviewed_solution_is_refused(self):
        for override in ({"solution_version": 0}, {"solution_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidSignaturePackageError):
                    package(**override)

    def test_a_versionless_transformations_asset_is_refused(self):
        for override in (
            {"transformations_version": 0},
            {"transformations_version": -1},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidSignaturePackageError):
                    package(**override)

    def test_a_cross_tenant_transformations_asset_is_refused(self):
        foreign = transformations(solution(tenant_id=OTHER_TENANT))

        with self.assertRaises(SignatureTenantBoundaryError):
            package(transformations=foreign)

    def test_a_non_typed_transformations_asset_is_refused(self):
        with self.assertRaises(InvalidSignaturePackageError):
            package(transformations="thirteen shifts, trust me")


if __name__ == "__main__":
    unittest.main()
