"""Aggregates for the Governance bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Mapping

from redops.contexts.governance.domain.errors import (
    AmbiguousAssetPackageError,
    ApprovalAuthorityError,
    ApprovalExpiredError,
    AssetPackageMismatchError,
    CheckpointMismatchError,
    CrossTenantGateError,
    GateDecisionError,
    GateLedgerError,
    PrerequisiteMismatchError,
    SelfApprovalError,
    StageGateNotAcceptedError,
    UnapprovedAssetError,
    UnknownStageError,
    UnsatisfiedPrerequisiteError,
)
from redops.contexts.governance.domain.value_objects import (
    ApprovalOutcome,
    AssetVersionRef,
    GateDisposition,
    GateState,
    StageAssetVersion,
    StageStatus,
    StageTemplate,
    StageTransition,
    Waiver,
    duplicate_asset_kinds,
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
    checkpoint: str = ""
    dependencies: frozenset[int] = field(default_factory=frozenset)
    asset_approvals: tuple["ApprovalRequest", ...] = ()
    state: GateState = GateState.NOT_STARTED
    proposed_by: str | None = None
    approver: str | None = None
    waiver: Waiver | None = None

    @classmethod
    def from_template(
        cls,
        template: StageTemplate,
        stage_number: int,
        asset_versions: Mapping[str, int],
    ) -> StageGate:
        """Build the canonical gate for a stage from the pipeline template.

        Dependencies, template version, and the required asset kinds come
        from the template rather than the caller, so an application boundary
        cannot under-declare a gate's prerequisites or its asset package. The
        caller supplies only the exact version pinned for each required asset
        kind (SPEC.md sections 3 and 4).
        """
        definition = template.definition_for(stage_number)
        if definition is None:
            raise UnknownStageError(
                f"stage {stage_number} is not defined in template "
                f"{template.version!r}"
            )

        supplied = set(asset_versions)
        missing = definition.required_asset_kinds - supplied
        extra = supplied - definition.required_asset_kinds
        if missing or extra:
            detail: list[str] = []
            if missing:
                detail.append(f"missing asset kinds: {', '.join(sorted(missing))}")
            if extra:
                detail.append(
                    f"unexpected asset kinds: {', '.join(sorted(extra))}"
                )
            raise AssetPackageMismatchError(
                f"stage {stage_number} asset package does not match template "
                f"{template.version!r}: {'; '.join(detail)}"
            )

        return cls(
            stage_number=stage_number,
            template_version=template.version,
            required_assets=frozenset(
                AssetVersionRef(kind, version)
                for kind, version in asset_versions.items()
            ),
            checkpoint=definition.checkpoint,
            dependencies=definition.dependencies,
        )

    @classmethod
    def from_assets(
        cls,
        template: StageTemplate,
        stage_number: int,
        *,
        tenant_id: str,
        assets: Iterable[StageAssetVersion],
    ) -> StageGate:
        """Build a stage gate from the real assets owned by one workspace.

        Each real ``StageAssetVersion`` is pinned for the workspace tenant, so a
        cross-tenant asset is refused rather than silently pinned as evidence
        (SPEC.md sections 3 and 11: every child resource belongs to exactly one
        client). The template still owns the required asset kinds, so a missing
        kind and an unexpected kind are refused by ``from_template``; an asset
        that leaves the exact version at issue ambiguous is refused here so one
        kind never silently overwrites another (SPEC.md sections 3 and 4).
        """
        versions: dict[str, int] = {}
        for asset in assets:
            pinned = asset.pin(tenant_id=tenant_id)
            if pinned.asset_id in versions:
                raise AmbiguousAssetPackageError(
                    f"stage {stage_number} package declares more than one exact "
                    f"version for asset kind {pinned.asset_id!r}"
                )
            versions[pinned.asset_id] = pinned.version
        return cls.from_template(template, stage_number, versions)

    def missing_assets(self, on: date, scope: str) -> frozenset[AssetVersionRef]:
        return frozenset(
            self.required_assets - self.approved_assets(on, scope)
        )

    def approved_assets(
        self, on: date, scope: str
    ) -> frozenset[AssetVersionRef]:
        """Required asset versions evidenced by an approved, in-scope request.

        The set is derived from the gate's durable ``ApprovalRequest``s, not
        self-declared, so the assets the policy evaluates are the evidence a
        passing ``GateDecision`` pins. An approval for another version, a
        request that is not approved, an approval already expired at the
        evaluation instant ``on``, and an approval for another intended
        downstream scope do not evidence a pinned asset. This reuses
        ``ApprovalRequest.authorizes`` so the gate and the durable
        ``GateDecision`` apply the same version, scope and expiry rule (SPEC.md
        sections 3, 4 and 11: a passing gate pins "the exact evidence and
        intended downstream use"; "a failed or expired prerequisite blocks
        dependent authorization until resolved").
        """
        return frozenset(
            asset
            for asset in self.required_assets
            if any(
                approval.authorizes(asset, scope, on)
                for approval in self.asset_approvals
            )
        )

    def record_asset_approval(self, request: "ApprovalRequest") -> None:
        """Record a version-specific approval for a required asset of this gate.

        Recording an approval for an asset outside the gate's required package
        is refused so the gate cannot accrue approvals for unrelated assets.
        """
        if request.asset not in self.required_assets:
            raise AssetPackageMismatchError(
                f"approval is for {request.asset}, which is not in the gate's "
                "required asset package"
            )
        self.asset_approvals = (*self.asset_approvals, request)

    def authorizes_downstream(self, on: date, scope: str) -> bool:
        return self.state is GateState.APPROVED and not self.missing_assets(
            on, scope
        )


@dataclass(frozen=True)
class GateDecision:
    """The durable, immutable record of a stage gate decision (SPEC.md section 3).

    It persists the stage, the pinned required asset versions, the checkpoint
    evidence, the canonical prerequisite stages, the reviewer, the intended
    downstream scope, the disposition, the rationale and the next action. It also
    persists the assigned work owner and due date so the production view can
    answer who is accountable for the stage and when the next approval is due
    (SPEC.md section 4). Persisting the prerequisite stages means a durable
    decision read in isolation can answer "which dependency blocks work" without
    consulting the in-memory ledger. Every disposition must
    pin the stage's required asset package, exactly one exact version per kind, so
    the durable record always says which versions the decision concerns, even
    when it blocks, requests changes, waives or supersedes. A passing decision
    pins the exact evidence and intended downstream use; a non-passing
    disposition, including a waiver, never authorizes downstream work. History
    is append-only: a later decision supersedes an earlier one by being recorded
    alongside it, never by editing.
    """

    stage_number: int
    template_version: str
    required_assets: frozenset[AssetVersionRef]
    checkpoint: str
    checkpoint_evidence: str
    reviewer: str
    scope: str
    disposition: GateDisposition
    rationale: str
    decided_on: date
    assigned_owner: str
    due_on: date
    dependencies: frozenset[int]
    next_action: str = ""
    waiver: Waiver | None = None
    asset_approvals: tuple["ApprovalRequest", ...] = ()
    blockers: frozenset[str] = frozenset()
    tenant_id: str = ""

    def __post_init__(self) -> None:
        if self.stage_number < 0:
            raise GateDecisionError("gate decision stage number must be >= 0")
        if not self.template_version or not self.template_version.strip():
            raise GateDecisionError("gate decision template version is required")
        if self.tenant_id and not self.tenant_id.strip():
            raise CrossTenantGateError(
                "a gate decision tenant id must be non-blank when carried"
            )
        if not self.reviewer or not self.reviewer.strip():
            raise GateDecisionError("gate decision reviewer is required")
        if not self.rationale or not self.rationale.strip():
            raise GateDecisionError("gate decision rationale is required")
        if not self.assigned_owner or not self.assigned_owner.strip():
            raise GateDecisionError(
                "gate decision assigned work owner is required for every stage"
            )
        if not isinstance(self.due_on, date):
            raise GateDecisionError(
                "gate decision due date is required for every stage"
            )
        if not self.checkpoint or not self.checkpoint.strip():
            raise GateDecisionError(
                "a gate decision must pin the checkpoint rubric for its stage"
            )

        for dependency in self.dependencies:
            if dependency < 0:
                raise GateDecisionError(
                    "gate decision prerequisite stage numbers must be >= 0"
                )
        if self.stage_number in self.dependencies:
            raise GateDecisionError(
                "a gate decision cannot list its own stage as a prerequisite"
            )

        if not self.required_assets:
            raise GateDecisionError(
                "a gate decision must pin the required asset versions for its "
                "stage, whatever the disposition"
            )
        duplicates = duplicate_asset_kinds(self.required_assets)
        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise AmbiguousAssetPackageError(
                "a gate decision must pin exactly one exact version per asset "
                f"kind; multiple versions declared for: {names}"
            )

        for blocker in self.blockers:
            if not blocker or not blocker.strip():
                raise GateDecisionError(
                    "gate decision blockers must be non-empty identifiers"
                )

        if self.disposition.is_passing:
            if not self.checkpoint_evidence or not self.checkpoint_evidence.strip():
                raise GateDecisionError(
                    "a passing gate decision must record checkpoint evidence"
                )
            if not self.scope or not self.scope.strip():
                raise GateDecisionError(
                    "a passing gate decision must record its intended downstream scope"
                )
            if self.waiver is not None:
                raise GateDecisionError(
                    "a passing gate decision cannot be recorded as a waiver"
                )
            unapproved = self.unapproved_assets()
            if unapproved:
                names = ", ".join(sorted(str(asset) for asset in unapproved))
                raise UnapprovedAssetError(
                    "a passing gate decision requires a recorded per-asset "
                    "approval for each pinned asset version and scope; "
                    f"unapproved: {names}"
                )

        if self.disposition is GateDisposition.WAIVED:
            if self.waiver is None:
                raise GateDecisionError(
                    "a waived gate decision requires a scoped waiver with a "
                    "risk owner"
                )
            if not self.scope or not self.scope.strip():
                raise GateDecisionError(
                    "a waived gate decision must record the intended downstream "
                    "scope it waives for"
                )
            broader = self.waiver.downstream_effects - frozenset({self.scope})
            if broader:
                names = ", ".join(sorted(broader))
                raise GateDecisionError(
                    "a waiver cannot claim downstream effects broader than the "
                    f"gate decision scope {self.scope!r}: {names}"
                )
            if self.waiver.is_expired(self.decided_on):
                raise GateDecisionError(
                    "a waived gate decision cannot record a scoped waiver that "
                    "has already expired at the decision instant; an expired "
                    "waiver is not a live risk acceptance (SPEC.md section 4)"
                )

    @classmethod
    def from_gate(
        cls,
        gate: StageGate,
        *,
        ledger: GateLedger,
        reviewer: str,
        scope: str,
        checkpoint_evidence: str,
        disposition: GateDisposition,
        rationale: str,
        on: date,
        assigned_owner: str,
        due_on: date,
        next_action: str = "",
        waiver: Waiver | None = None,
        blockers: frozenset[str] | None = None,
        tenant_id: str | None = None,
    ) -> GateDecision:
        """Record a decision against a gate, refusing to coerce a bad gate.

        For a passing disposition the gate must pass GateIntegrityPolicy and
        authorize downstream use, and the reviewer must be the gate's designated
        approver. Prerequisite state and the canonical template are read from the
        durable ``GateLedger`` rather than a caller-supplied map, so an
        application boundary cannot inject an approved prerequisite that has no
        recorded ``GateDecision`` (SPEC.md section 4). This prevents recording an
        approval for a gate that is missing an exact asset version, has an
        unapproved prerequisite, or lacks a designated approver. The decision
        records the gate's own durable per-asset ``ApprovalRequest``s, so the
        evidence the decision pins is exactly the evidence the gate recorded and
        the policy evaluated; a caller cannot substitute a different approval
        set (SPEC.md sections 3 and 4).

        A waived disposition is also a human authority decision: it must name the
        gate's designated approver as its reviewer and cannot be recorded by the
        gate's author, so a stage cannot be self-waived to bypass a missing asset
        (SPEC.md sections 4 and 5).
        """
        if disposition.is_passing:
            from redops.contexts.governance.domain.policies import (
                GateIntegrityPolicy,
            )

            evaluation = GateIntegrityPolicy().evaluate(
                gate,
                ledger.dependency_states(on=on),
                ledger.template,
                on=on,
                scope=scope,
            )
            if not evaluation.approvable:
                raise GateDecisionError(
                    "cannot record an approval for a gate that is not approvable: "
                    + "; ".join(evaluation.reasons)
                )
            if reviewer != gate.approver:
                raise GateDecisionError(
                    f"reviewer {reviewer!r} is not the gate's designated "
                    f"approver {gate.approver!r}"
                )
            if not gate.authorizes_downstream(on, scope):
                raise GateDecisionError(
                    "gate does not authorize downstream use for this decision"
                )

        if disposition is GateDisposition.WAIVED:
            if not gate.approver or not gate.approver.strip():
                raise GateDecisionError(
                    "a waived gate decision requires the gate's designated "
                    "approver"
                )
            if reviewer != gate.approver:
                raise GateDecisionError(
                    f"reviewer {reviewer!r} is not the gate's designated "
                    f"approver {gate.approver!r}"
                )
            if gate.proposed_by and reviewer == gate.proposed_by:
                raise GateDecisionError(
                    "the gate's author cannot waive their own gate; a waiver is "
                    "a human authority decision"
                )

        resolved_blockers = blockers
        if resolved_blockers is None:
            if disposition is GateDisposition.BLOCKED:
                from redops.contexts.governance.domain.policies import (
                    GateIntegrityPolicy,
                )

                evaluation = GateIntegrityPolicy().evaluate(
                    gate,
                    ledger.dependency_states(on=on),
                    ledger.template,
                    on=on,
                    scope=scope,
                )
                resolved_blockers = frozenset(evaluation.reasons)
            else:
                resolved_blockers = frozenset()

        resolved_tenant = tenant_id if tenant_id is not None else ledger.tenant_id
        return cls(
            stage_number=gate.stage_number,
            template_version=gate.template_version,
            required_assets=gate.required_assets,
            checkpoint=gate.checkpoint,
            checkpoint_evidence=checkpoint_evidence,
            reviewer=reviewer,
            scope=scope,
            disposition=disposition,
            rationale=rationale,
            decided_on=on,
            assigned_owner=assigned_owner,
            due_on=due_on,
            dependencies=gate.dependencies,
            next_action=next_action,
            waiver=waiver,
            asset_approvals=gate.asset_approvals,
            blockers=frozenset(resolved_blockers),
            tenant_id=resolved_tenant,
        )

    @property
    def is_passing(self) -> bool:
        return self.disposition.is_passing

    def unapproved_assets(self) -> frozenset[AssetVersionRef]:
        """Pinned assets with no covering approved, in-scope, unexpired request.

        Evaluated at the instant the decision was recorded. Each asset must be
        approved for its exact version and the decision's intended downstream
        scope. A pending, rejected, superseded or expired request, a request for
        another version, or a request for another scope does not cover the
        pinned asset (SPEC.md sections 3, 4 and 11).
        """
        return self.unapproved_assets_at(self.decided_on)

    def unapproved_assets_at(self, on: date) -> frozenset[AssetVersionRef]:
        """Pinned assets not covered by a still-effective approval at ``on``.

        The same version, scope and expiry rule as ``unapproved_assets``, but
        evaluated at an arbitrary instant so a prerequisite decision can be
        re-checked long after it was recorded (SPEC.md section 4: "a failed or
        expired prerequisite blocks dependent authorization until resolved").
        """
        return frozenset(
            asset
            for asset in self.required_assets
            if not any(
                approval.authorizes(asset, self.scope, on)
                for approval in self.asset_approvals
            )
        )

    def authorizes_downstream(self) -> bool:
        return self.authorizes_downstream_at(self.decided_on)

    def authorizes_downstream_at(self, on: date) -> bool:
        """Whether this decision still authorizes its scope at instant ``on``.

        Structural authorization plus the exact pinned approvals are checked
        against the evaluation instant, so a passing decision whose approvals
        have since expired no longer authorizes dependent work.
        """
        return (
            self.is_passing
            and bool(self.required_assets)
            and bool(self.scope and self.scope.strip())
            and not self.unapproved_assets_at(on)
        )


class GateLedger:
    """Append-only ledger of stage gate decisions for one pipeline template.

    Each stage's current prerequisite state is derived from the durable
    ``GateDecision`` records the ledger holds, not from a caller-supplied map.
    A passing decision is refused while any prerequisite stage in the template
    lacks a passing decision, so an unapproved dependency can never authorize
    downstream work (SPEC.md section 4: "a failed or expired prerequisite blocks
    dependent authorization until resolved"). The template is data; named human
    approver identities remain an open decision.
    """

    def __init__(self, template: StageTemplate, tenant_id: str = "") -> None:
        if tenant_id and not tenant_id.strip():
            raise GateLedgerError(
                "a gate ledger tenant id must be non-blank when scoped"
            )
        self._template = template
        self._tenant_id = tenant_id
        self._decisions: dict[int, list[GateDecision]] = {}

    @property
    def template(self) -> StageTemplate:
        return self._template

    @property
    def tenant_id(self) -> str:
        """The client this ledger is scoped to, or "" for an unscoped ledger.

        A ledger reconstructed from a tenant-scoped repository carries that
        client's id, and every decision recorded through ``from_gate`` inherits
        it, so a decision can never be persisted without naming the client it
        authorizes (SPEC.md sections 3 and 9).
        """
        return self._tenant_id

    def record(self, decision: GateDecision) -> None:
        if decision.template_version != self._template.version:
            raise GateLedgerError(
                f"decision template version {decision.template_version!r} does "
                f"not match ledger template version {self._template.version!r}"
            )
        if self._tenant_id and decision.tenant_id != self._tenant_id:
            raise CrossTenantGateError(
                f"decision tenant {decision.tenant_id!r} does not match ledger "
                f"tenant {self._tenant_id!r}; a ledger authorizes exactly one "
                "client"
            )
        if self._template.definition_for(decision.stage_number) is None:
            raise UnknownStageError(
                f"stage {decision.stage_number} is not defined in template "
                f"{self._template.version!r}"
            )
        ambiguous = duplicate_asset_kinds(decision.required_assets)
        if ambiguous:
            names = ", ".join(sorted(ambiguous))
            raise AmbiguousAssetPackageError(
                "a decision must pin exactly one exact version per asset kind; "
                f"multiple versions declared for: {names}"
            )
        canonical_kinds = self._template.required_asset_kinds(
            decision.stage_number
        )
        declared_kinds = {asset.asset_id for asset in decision.required_assets}
        if declared_kinds != canonical_kinds:
            missing = sorted(canonical_kinds - declared_kinds)
            extra = sorted(declared_kinds - canonical_kinds)
            detail: list[str] = []
            if missing:
                detail.append(f"missing asset kinds: {', '.join(missing)}")
            if extra:
                detail.append(f"unexpected asset kinds: {', '.join(extra)}")
            raise AssetPackageMismatchError(
                f"stage {decision.stage_number} decision does not match "
                f"template {self._template.version!r} required asset package: "
                f"{'; '.join(detail)}"
            )
        canonical_checkpoint = self._template.definition_for(
            decision.stage_number
        ).checkpoint
        if decision.checkpoint != canonical_checkpoint:
            raise CheckpointMismatchError(
                f"stage {decision.stage_number} decision names checkpoint "
                f"{decision.checkpoint!r} but template "
                f"{self._template.version!r} requires {canonical_checkpoint!r}"
            )
        canonical_dependencies = self._template.dependencies_of(
            decision.stage_number
        )
        if decision.dependencies != canonical_dependencies:
            raise PrerequisiteMismatchError(
                f"stage {decision.stage_number} decision names prerequisites "
                f"{sorted(decision.dependencies)} but template "
                f"{self._template.version!r} requires "
                f"{sorted(canonical_dependencies)}"
            )
        if decision.is_passing:
            unsatisfied = sorted(
                stage
                for stage in self._template.dependencies_of(decision.stage_number)
                if not self.has_passing_decision(
                    stage, on=decision.decided_on
                )
            )
            if unsatisfied:
                names = ", ".join(str(stage) for stage in unsatisfied)
                raise UnsatisfiedPrerequisiteError(
                    f"stage {decision.stage_number} cannot pass while "
                    f"prerequisite stages lack a passing decision: {names}"
                )
        self._decisions.setdefault(decision.stage_number, []).append(decision)

    def decisions_for(self, stage_number: int) -> tuple[GateDecision, ...]:
        return tuple(self._decisions.get(stage_number, ()))

    def decision_for(self, stage_number: int) -> GateDecision | None:
        entries = self._decisions.get(stage_number)
        return entries[-1] if entries else None

    def has_passing_decision(self, stage_number: int, *, on: date) -> bool:
        """Whether the stage and its whole prerequisite chain authorize at ``on``.

        A stage authorizes dependent work only when its latest decision is
        passing, its exact pinned approvals are still effective, and every
        transitive prerequisite stage also authorizes at the same instant. The
        template is acyclic and every dependency points to an earlier stage, so
        the recursion terminates. This closes the dependency graph at the
        evaluation instant: an expired approval anywhere upstream revokes every
        dependent stage until it is resolved (SPEC.md section 4: "a failed or
        expired prerequisite blocks dependent authorization until resolved").
        """
        latest = self.decision_for(stage_number)
        if latest is None or not latest.authorizes_downstream_at(on):
            return False
        return all(
            self.has_passing_decision(dependency, on=on)
            for dependency in self._template.dependencies_of(stage_number)
        )

    def dependency_states(self, *, on: date) -> Mapping[int, GateState]:
        """Prerequisite gate states, time-aware at the evaluation instant.

        A latest passing decision that no longer authorizes at ``on`` — because
        its own pinned approvals have expired or because a transitive
        prerequisite has lapsed — is reported as ``BLOCKED`` rather than
        ``APPROVED``: the stage no longer authorizes dependent work even though
        no newer decision has been recorded. There is no separate expired gate
        state in SPEC.md section 4, and an expired prerequisite is exactly a
        blocked dependency.
        """
        states: dict[int, GateState] = {}
        for stage in self._template.stages:
            latest = self.decision_for(stage.stage_number)
            if latest is None:
                states[stage.stage_number] = GateState.NOT_STARTED
            elif latest.is_passing and not self.has_passing_decision(
                stage.stage_number, on=on
            ):
                states[stage.stage_number] = GateState.BLOCKED
            else:
                states[stage.stage_number] = self._gate_state(latest.disposition)
        return states

    @staticmethod
    def _gate_state(disposition: GateDisposition) -> GateState:
        return {
            GateDisposition.APPROVED: GateState.APPROVED,
            GateDisposition.CHANGES_REQUIRED: GateState.CHANGES_REQUIRED,
            GateDisposition.BLOCKED: GateState.BLOCKED,
            GateDisposition.WAIVED: GateState.WAIVED,
            GateDisposition.SUPERSEDED: GateState.SUPERSEDED,
        }[disposition]


@dataclass
class StageRun:
    """One execution of a production stage (0-10) for an engagement.

    A StageRun is complete only when its gate is accepted for downstream use;
    recording activity starts or keeps a stage Working but never completes it
    (SPEC.md sections 3 and 4). Every status change is recorded with actor,
    reason, timestamp, old and new status, and a correlation ID; illegal
    transitions are rejected rather than silently coerced.
    """

    engagement: str
    stage_number: int
    template_version: str
    assigned_owner: str
    status: StageStatus = StageStatus.NOT_STARTED
    entered_at: date | None = None
    exited_at: date | None = None
    accepted_decision: GateDecision | None = None
    waiver_decision: GateDecision | None = None
    _transitions: list[StageTransition] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not self.engagement or not self.engagement.strip():
            raise ValueError("stage run engagement is required")
        if self.stage_number < 0:
            raise ValueError("stage number must be >= 0")
        if not self.template_version or not self.template_version.strip():
            raise ValueError("stage run template version is required")
        if not self.assigned_owner or not self.assigned_owner.strip():
            raise ValueError("stage run assigned owner is required")

    @property
    def is_complete(self) -> bool:
        return self.status is StageStatus.COMPLETE

    @property
    def transitions(self) -> tuple[StageTransition, ...]:
        return tuple(self._transitions)

    def record_activity(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> StageTransition | None:
        """Note that work happened. Activity starts a stage but never completes it."""
        if self.status is StageStatus.NOT_STARTED:
            return self.start(
                actor=actor, reason=reason, on=on, correlation_id=correlation_id
            )
        return None

    def start(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> StageTransition:
        transition = self._transition(
            StageStatus.WORKING,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )
        if self.entered_at is None:
            self.entered_at = on
        return transition

    def submit_for_review(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> StageTransition:
        return self._transition(
            StageStatus.IN_REVIEW,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def send_back(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> StageTransition:
        return self._transition(
            StageStatus.CHANGES_REQUIRED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def block(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> StageTransition:
        return self._transition(
            StageStatus.BLOCKED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def unblock(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> StageTransition:
        return self._transition(
            StageStatus.WORKING,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def supersede(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> StageTransition:
        return self._transition(
            StageStatus.SUPERSEDED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def complete(
        self,
        *,
        decision: GateDecision,
        ledger: GateLedger,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> StageTransition:
        """Complete the stage only with an accepted decision for this exact stage.

        Completion must be backed by the durable GateDecision, not a transient
        gate object, so the stage pins the exact evidence the reviewer accepted.
        The decision must be for this stage and template version and must
        authorize downstream use at the transition instant. An accepted
        decision whose pinned per-asset approvals have since expired no longer
        authorizes the completion, so a stage cannot be marked complete on
        stale evidence (SPEC.md section 4: "a failed or expired prerequisite
        blocks dependent authorization until resolved"). Activity alone never
        reaches here.

        The durable ``GateLedger`` is consulted for the stage's transitive
        prerequisite chain. The accepted decision carries no upstream state, so
        a stage whose own approvals are current could otherwise complete on top
        of a prerequisite that has lapsed. The completion is refused unless
        every prerequisite stage authorizes at the transition instant.

        The ledger is also the stage's durable decision record. A caller-supplied
        passing ``GateDecision`` the ledger never recorded is a transient object,
        not the accepted gate, and a later durable decision for the same stage
        supersedes the pass, so completion must be authorized by the stage's
        *current* recorded decision, not merely by a decision that once passed
        (SPEC.md sections 3 and 4).
        """
        if decision.stage_number != self.stage_number:
            raise StageGateNotAcceptedError(
                f"decision is for stage {decision.stage_number}, "
                f"not stage {self.stage_number}"
            )
        if decision.template_version != self.template_version:
            raise StageGateNotAcceptedError(
                f"decision template version {decision.template_version!r} does "
                f"not match stage template version {self.template_version!r}"
            )
        if ledger.template.version != self.template_version:
            raise StageGateNotAcceptedError(
                f"ledger template version {ledger.template.version!r} does "
                f"not match stage template version {self.template_version!r}"
            )
        if not decision.authorizes_downstream_at(on):
            raise StageGateNotAcceptedError(
                "decision is not passing, has no intended downstream scope, "
                "or its pinned approvals have expired at the transition instant"
            )
        recorded = ledger.decision_for(self.stage_number)
        if recorded is None:
            raise StageGateNotAcceptedError(
                f"stage {self.stage_number} has no durable gate decision "
                "recorded in the ledger"
            )
        if recorded is not decision:
            raise StageGateNotAcceptedError(
                "the accepted decision is not the stage's current durable "
                "ledger decision"
            )
        unsatisfied = sorted(
            dependency
            for dependency in ledger.template.dependencies_of(self.stage_number)
            if not ledger.has_passing_decision(dependency, on=on)
        )
        if unsatisfied:
            names = ", ".join(str(stage) for stage in unsatisfied)
            raise StageGateNotAcceptedError(
                "stage cannot complete while prerequisite stages lack a "
                f"passing, unexpired decision at the transition instant: {names}"
            )
        transition = self._transition(
            StageStatus.COMPLETE,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )
        self.exited_at = on
        self.accepted_decision = decision
        return transition

    def waive(
        self,
        *,
        waiver: Waiver,
        decision: GateDecision,
        ledger: GateLedger,
        actor: str,
        on: date,
        correlation_id: str,
    ) -> StageTransition:
        """Mirror a durable scoped gate waiver onto the stage.

        SPEC.md section 4 lists ``Waived`` among the stage states and requires a
        waiver to be a scoped human decision with a reason, risk owner, expiry or
        review trigger, and downstream effects; a waiver never makes an absent
        asset appear present. The transition policy permits only
        ``WORKING -> WAIVED``, so a not-started, in-review, completed or already
        superseded stage is refused rather than silently coerced.

        The waiver must be the exact scoped waiver recorded on the stage's
        current durable ``GateDecision`` and that decision must be recorded in
        the ``GateLedger``. A caller-supplied ``Waiver`` that no recorded human
        decision backs is a transient bypass, so ``waive()`` applies the same
        durability discipline as ``complete()``: the decision must be for this
        stage and template version, must be a ``WAIVED`` disposition, must carry
        the same waiver the caller names, and must be the stage's current entry
        in the ledger. A scoped waiver whose own expiry has passed at the
        transition instant is no longer a live risk acceptance, so it cannot be
        mirrored onto the stage (SPEC.md section 4). The waiver reason is
        recorded on the transition, the exact durable ``GateDecision`` is
        retained on ``waiver_decision`` so the production view can show the
        scoped risk owner, expiry or review trigger, downstream effects, reviewer
        and next action, and ``accepted_decision`` and ``exited_at`` are never
        set, so a waived stage is never represented as complete.
        """
        if waiver is None:
            raise ValueError("a stage waiver requires a scoped Waiver")
        if decision.stage_number != self.stage_number:
            raise StageGateNotAcceptedError(
                f"waiver decision is for stage {decision.stage_number}, "
                f"not stage {self.stage_number}"
            )
        if decision.template_version != self.template_version:
            raise StageGateNotAcceptedError(
                f"waiver decision template version "
                f"{decision.template_version!r} does not match stage template "
                f"version {self.template_version!r}"
            )
        if ledger.template.version != self.template_version:
            raise StageGateNotAcceptedError(
                f"ledger template version {ledger.template.version!r} does "
                f"not match stage template version {self.template_version!r}"
            )
        if decision.disposition is not GateDisposition.WAIVED:
            raise StageGateNotAcceptedError(
                "a stage can only be waived by a gate decision whose "
                f"disposition is WAIVED, not {decision.disposition.value!r}"
            )
        if decision.waiver != waiver:
            raise StageGateNotAcceptedError(
                "the accepted waiver decision is not recorded for the named "
                "scoped waiver"
            )
        if waiver.is_expired(on):
            raise StageGateNotAcceptedError(
                "the scoped waiver has expired at the transition instant, so it "
                "no longer authorizes a waived stage; SPEC.md section 4 requires "
                "a failed or expired prerequisite to be resolved first"
            )
        recorded = ledger.decision_for(self.stage_number)
        if recorded is None:
            raise StageGateNotAcceptedError(
                f"stage {self.stage_number} has no durable gate decision "
                "recorded in the ledger"
            )
        if recorded is not decision:
            raise StageGateNotAcceptedError(
                "the accepted waiver decision is not the stage's current "
                "durable ledger decision"
            )
        transition = self._transition(
            StageStatus.WAIVED,
            actor=actor,
            reason=waiver.reason,
            on=on,
            correlation_id=correlation_id,
        )
        self.waiver_decision = decision
        return transition

    def _transition(
        self,
        target: StageStatus,
        *,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> StageTransition:
        from redops.contexts.governance.domain.policies import StageTransitionPolicy

        previous = self.status
        StageTransitionPolicy().require(previous, target)
        self.status = target
        transition = StageTransition(
            actor=actor,
            reason=reason,
            occurred_at=on,
            old_status=previous,
            new_status=target,
            correlation_id=correlation_id,
        )
        self._transitions.append(transition)
        return transition


@dataclass(frozen=True)
class Decision:
    """An append-only governance decision record (SPEC.md section 3).

    A decision names its subject, the exact affected version, the choice, the
    actor, the timestamp and the rationale. It is never edited or deleted; a
    new decision supersedes an earlier one by being appended alongside it.
    """

    subject: str
    choice: str
    rationale: str
    actor: str
    decided_on: date
    affected_version: AssetVersionRef | None = None

    def __post_init__(self) -> None:
        if not self.subject or not self.subject.strip():
            raise ValueError("decision subject is required")
        if not self.choice or not self.choice.strip():
            raise ValueError("decision choice is required")
        if not self.rationale or not self.rationale.strip():
            raise ValueError("decision rationale is required")
        if not self.actor or not self.actor.strip():
            raise ValueError("decision actor is required")


class DecisionLog:
    """Append-only history of governance decisions.

    The log exposes no update or delete operation by design: decision history
    is append only. Reads return immutable tuples so callers cannot mutate the
    stored history.
    """

    def __init__(self) -> None:
        self._entries: list[Decision] = []

    def record(self, decision: Decision) -> None:
        self._entries.append(decision)

    @property
    def entries(self) -> tuple[Decision, ...]:
        return tuple(self._entries)

    def for_subject(self, subject: str) -> tuple[Decision, ...]:
        return tuple(entry for entry in self._entries if entry.subject == subject)


@dataclass
class ApprovalRequest:
    """A version-specific request for a designated human approval.

    Approval pins one exact asset version and one intended downstream scope.
    The requester can never be the approver, and only the designated approver
    can decide. An approval authorizes exactly the version and scope it pins,
    until it expires or is superseded (SPEC.md sections 3, 4 and 11).
    """

    asset: AssetVersionRef
    scope: str
    requested_by: str
    approver: str
    outcome: ApprovalOutcome = ApprovalOutcome.PENDING
    expires_on: date | None = None

    def __post_init__(self) -> None:
        if not self.scope or not self.scope.strip():
            raise ValueError("approval scope is required")
        if not self.requested_by or not self.requested_by.strip():
            raise ValueError("approval requester is required")
        if not self.approver or not self.approver.strip():
            raise ValueError("approval approver is required")
        if self.approver == self.requested_by:
            raise SelfApprovalError("author cannot be the designated approver")

    def is_expired(self, on: date) -> bool:
        return self.expires_on is not None and on > self.expires_on

    def authorizes(self, asset: AssetVersionRef, scope: str, on: date) -> bool:
        return (
            self.outcome is ApprovalOutcome.APPROVED
            and self.asset == asset
            and self.scope == scope
            and not self.is_expired(on)
        )

    def approve(self, *, actor: str, on: date, rationale: str = "approved") -> Decision:
        if actor != self.approver:
            raise ApprovalAuthorityError(
                f"{actor!r} is not the designated approver {self.approver!r}"
            )
        if self.is_expired(on):
            raise ApprovalExpiredError("approval request has expired")
        self.outcome = ApprovalOutcome.APPROVED
        return self._decision(ApprovalOutcome.APPROVED, actor, on, rationale)

    def reject(self, *, actor: str, on: date, rationale: str) -> Decision:
        if actor != self.approver:
            raise ApprovalAuthorityError(
                f"{actor!r} is not the designated approver {self.approver!r}"
            )
        self.outcome = ApprovalOutcome.REJECTED
        return self._decision(ApprovalOutcome.REJECTED, actor, on, rationale)

    def supersede(
        self,
        *,
        actor: str,
        on: date,
        rationale: str,
        log: DecisionLog | None = None,
    ) -> Decision:
        self.outcome = ApprovalOutcome.SUPERSEDED
        decision = self._decision(ApprovalOutcome.SUPERSEDED, actor, on, rationale)
        if log is not None:
            log.record(decision)
        return decision

    def _decision(
        self,
        outcome: ApprovalOutcome,
        actor: str,
        on: date,
        rationale: str,
    ) -> Decision:
        return Decision(
            subject=self.asset.asset_id,
            choice=outcome.value,
            rationale=rationale,
            actor=actor,
            decided_on=on,
            affected_version=self.asset,
        )
