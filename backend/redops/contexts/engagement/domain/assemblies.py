"""Stage 0 gate assembly for the Engagement bounded context (pure domain).

SPEC.md section 4 makes the stage 0 "Intake" gate the first checkpoint of the
stage 0-10 pipeline: the stage is complete only when its required assets exist,
pass the "Production Ready" checkpoint, and receive approval for downstream use,
and a passing gate pins the exact asset versions and intended use. The
``IntakePackage`` (Engagement value object) holds the twelve real stage 0 assets,
the governance ``StageGate.from_assets`` pins them as exact ``AssetVersionRef``
evidence, ``ProductionReadyPolicy`` evaluates the checkpoint, and
``GateApproverAuthorityPolicy`` binds the gate's designated approver to the
workspace authority registry.

This assembler composes those pieces so a caller cannot hand an under-declared
or unvalidated stage 0 gate to ``GateDecision.from_gate``. It is a pure domain
service: it returns a gate and mutates nothing, invokes no persistence, and never
invents a concrete approver identity or authority role, which remain open
decisions supplied by the client workspace (SPEC.md section 11).
"""

from __future__ import annotations

from typing import Iterable

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.policies import (
    GateApproverAuthorityPolicy,
    ProductionReadyPolicy,
)
from redops.contexts.engagement.domain.value_objects import IntakePackage
from redops.contexts.governance.domain.entities import StageGate
from redops.contexts.governance.domain.value_objects import StageTemplate
from redops.contexts.knowledge.domain.entities import Claim

STAGE_ZERO = 0


class StageZeroGateAssembler:
    """Builds and validates the canonical stage 0 gate for one client workspace.

    The package must be production ready (every canonical asset kind present,
    each owned by a named workspace authority, each evidenced by a same-tenant,
    known, directly sourced claim), the assembled gate must pin the template's
    exact stage 0 asset package, and the designated approver must be a named
    authority on the same workspace. A caller-supplied gate that skips any of
    these steps is exactly what this assembler replaces (SPEC.md sections 3, 4
    and 5).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: IntakePackage,
        approver: str,
        claims: Iterable[Claim],
        proposed_by: str | None = None,
    ) -> StageGate:
        ProductionReadyPolicy().require(package, workspace, claims)
        gate = StageGate.from_assets(
            template,
            STAGE_ZERO,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate
