"""RED HTTP routes.

These routes are thin adapters. The stages route exposes the canonical 0-10
production template as read-only reference data from the pure Governance domain
(`stage_zero_to_ten_template`, SPEC.md section 4); it computes no domain rule,
holds no state and mutates nothing. Gate integrity, approval authority and
tenant scoping stay in the domain and application layers where they are
enforced and tested.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from redops.contexts.governance.domain.templates import stage_zero_to_ten_template

router = APIRouter(prefix="/red", tags=["red"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the RED app."""

    return {"status": "ok"}


@router.get("/stages")
def stages() -> list[dict[str, Any]]:
    """Return the canonical stages 0-10 and their checkpoints.

    The template is data: it names roles, not people, and confers no authority.
    """

    template = stage_zero_to_ten_template()
    return [
        {
            "stage_number": stage.stage_number,
            "name": stage.name,
            "checkpoint": stage.checkpoint,
            "required_asset_kinds": sorted(stage.required_asset_kinds),
            "accountable_role": stage.accountable_role,
            "approver_role": stage.approver_role,
            "dependencies": sorted(stage.dependencies),
        }
        for stage in template.stages
    ]
