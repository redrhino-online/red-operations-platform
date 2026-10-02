"""Aggregates for the Governance bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass, field

from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateState,
    Waiver,
)


@dataclass
class StageGate:
    """A gate on one production stage (0-10).

    A gate authorizes downstream work only when it is Approved and every required
    exact asset version is present and approved. A waiver never substitutes for
    an absent asset, and dependencies are enforced by GateIntegrityPolicy.
    """

    stage_number: int
    template_version: str
    required_assets: frozenset[AssetVersionRef]
    dependencies: frozenset[int] = field(default_factory=frozenset)
    approved_assets: frozenset[AssetVersionRef] = field(default_factory=frozenset)
    state: GateState = GateState.NOT_STARTED
    proposed_by: str | None = None
    approver: str | None = None
    waiver: Waiver | None = None

    def missing_assets(self) -> frozenset[AssetVersionRef]:
        return frozenset(self.required_assets - self.approved_assets)

    def authorizes_downstream(self) -> bool:
        return self.state is GateState.APPROVED and not self.missing_assets()
