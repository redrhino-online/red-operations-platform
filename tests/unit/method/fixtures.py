"""Shared pure-domain fixtures for Method tests.

These build valid stage 2 and stage 3 assets so tests that approve a
MethodVersion can pin its required upstream dependencies without restating the
same content in every file. They are test data only and carry no behavior.
"""

from __future__ import annotations

from redops.contexts.method.domain.entities import DiagnosticModel
from redops.contexts.method.domain.value_objects import (
    PrimaryCurrency,
    ProfitPyramidLevel,
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
    )
