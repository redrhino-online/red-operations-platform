"""Shared pure-domain fixtures for Method tests.

These build valid stage 2, stage 3 and stage 4 assets so tests that approve a
MethodVersion can pin its required upstream dependencies without restating the
same content in every file. They are test data only and carry no behavior.
"""

from __future__ import annotations

from redops.contexts.method.domain.entities import DiagnosticModel, SignatureSolution
from redops.contexts.method.domain.value_objects import (
    PrimaryCurrency,
    ProfitPyramidLevel,
    SignatureStep,
    TransformationPhase,
)

TENANT = "client-3f"


def primary_currency(tenant_id: str = TENANT) -> PrimaryCurrency:
    return PrimaryCurrency(
        tenant_id=tenant_id,
        currency="qualified referrals",
        audience="owner-operators of two to five person service firms",
        current_measure="4 qualified referrals per month",
        desired_measure="12 qualified referrals per month",
        mechanism="referral partner network",
    )


def level(
    level_id: str,
    name: str,
    measure: str,
    tenant_id: str = TENANT,
) -> ProfitPyramidLevel:
    return ProfitPyramidLevel(
        level_id=level_id,
        tenant_id=tenant_id,
        name=name,
        observable_measures=(measure,),
        symptoms=(f"{name} symptoms",),
        behaviors=(f"{name} behaviors",),
        problems=(f"{name} problems",),
    )


def diagnostic_model(tenant_id: str = TENANT) -> DiagnosticModel:
    return DiagnosticModel(
        model_id="model-3f",
        tenant_id=tenant_id,
        name="Growth Pyramid",
        levels=(
            level("level-1", "Stuck", "under 4 qualified referrals per month", tenant_id),
            level("level-2", "Scaling", "12 or more qualified referrals per month", tenant_id),
        ),
        progression="climb from Stuck to Scaling by installing the referral network",
        qualification_logic="rank the prospect by observable monthly referral count",
        visual="asset://diagnostic/3f-growth-pyramid.png",
        explanatory_copy=(
            "Four levels from Stuck to Scaling, each placed by observable "
            "monthly referral count"
        ),
    )


def signature_step(
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


def signature_solution(tenant_id: str = TENANT) -> SignatureSolution:
    steps = (
        signature_step("step-1", "Diagnose", "chaotic", "diagnosed", tenant_id),
        signature_step("step-2", "Position", "diagnosed", "positioned", tenant_id),
        signature_step("step-3", "Model", "positioned", "modeled", tenant_id),
        signature_step("step-4", "Package IP", "modeled", "packaged", tenant_id),
        signature_step("step-5", "Productize", "packaged", "productized", tenant_id),
        signature_step("step-6", "Message", "productized", "messaged", tenant_id),
        signature_step("step-7", "Produce", "messaged", "produced", tenant_id),
        signature_step("step-8", "Integrate", "produced", "integrated", tenant_id),
        signature_step("step-9", "Launch", "integrated", "launched", tenant_id),
    )
    phases = (
        TransformationPhase("phase-1", tenant_id, "Diagnose and Position", steps[0:3]),
        TransformationPhase("phase-2", tenant_id, "Package and Productize", steps[3:6]),
        TransformationPhase("phase-3", tenant_id, "Produce and Launch", steps[6:9]),
    )
    return SignatureSolution(
        solution_id="solution-3f",
        tenant_id=tenant_id,
        transformation_map="from chaotic delivery to a launched campaign",
        process_inventory=("diagnose", "position", "model", "package", "productize"),
        phases=phases,
        starting_state="chaotic",
        final_state="launched",
        narrative="the client moves from unpredictable work to a repeatable growth system",
        visual="asset://transformations/3f-map.png",
    )
