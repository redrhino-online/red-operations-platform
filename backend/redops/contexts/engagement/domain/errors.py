"""Named domain errors for the Engagement bounded context (pure domain)."""

from __future__ import annotations


class EngagementError(Exception):
    """Base class for engagement domain rule violations."""


class InvalidClientWorkspaceError(EngagementError, ValueError):
    """A ClientWorkspace was built or changed without its required identity.

    SPEC.md section 3: the ClientWorkspace aggregate carries an id, a tenant, its
    authorities and a lifecycle. A workspace that leaves its opaque id, tenant or
    authority registry unspecified cannot anchor any client-owned resource.
    """


class InvalidAuthorityError(EngagementError, ValueError):
    """A ClientAuthority was built without a named actor or authority.

    SPEC.md section 3: the workspace records its authorities, and SPEC.md section
    4 requires named human owners. An authority entry that names neither an actor
    nor the authority it holds is not a usable authority record.
    """


class TenantBoundaryError(EngagementError):
    """A child resource from another client was attached to this workspace.

    SPEC.md section 3: "Every child resource belongs to exactly one client." A
    child whose tenant is not this workspace's tenant belongs to a different
    client and cannot be attached here.
    """


class ChildAlreadyAttachedError(EngagementError):
    """A child resource was attached to the same workspace more than once.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    child already attached to this workspace cannot be attached a second time,
    which would leave its ownership ambiguous.
    """


class IllegalLifecycleTransitionError(EngagementError):
    """A ClientWorkspace was asked to move between lifecycle states its rules forbid.

    SPEC.md section 4: the engagement lifecycle must reject illegal transitions
    rather than silently coercing state. A workspace cannot skip, reverse or leave
    its terminal state.
    """


class InvalidIntakeAssetError(EngagementError, ValueError):
    """A stage 0 intake asset was built without its required identity or content.

    SPEC.md section 1: every output has a source, status, owner and next action.
    SPEC.md section 4, stage 0 "Intake": the required asset package names the
    client record, signed scope, billing confirmation, questionnaire, brand asset
    inventory, access checklist, baseline measures, workspace, communication
    channel, timeline, responsibilities and launch definition. An asset that
    leaves its kind, owner, summary or source unspecified cannot be represented
    as a real intake asset.
    """


class InvalidIntakePackageError(EngagementError, ValueError):
    """A stage 0 intake package was built with inconsistent or duplicate assets.

    SPEC.md section 4, stage 0 "Intake": the required asset package is the set of
    named assets behind the "Production Ready" checkpoint, and SPEC.md section 3
    requires every child resource to belong to exactly one client. A package that
    repeats an asset kind or mixes tenants cannot be represented as a coherent
    intake package.
    """


class IncompleteIntakePackageError(EngagementError):
    """A stage 0 intake package was asked to be production ready while incomplete.

    SPEC.md section 4, stage 0 and its "Production Ready" checkpoint: "building
    for whom, success measure, owners, boundaries, and prerequisites are
    explicit". Every canonical stage 0 asset kind must be present, so a missing
    asset is surfaced rather than hidden behind a passed gate.
    """


class IntakeOwnerNotAuthorizedError(EngagementError):
    """A stage 0 intake asset names an owner who holds no authority.

    SPEC.md section 4: a stage completion has an assigned owner, and SPEC.md
    section 1 requires every output to have an owner. An owner who is not a named
    authority on the client workspace cannot be accountable for the asset.
    """


class GateApproverNotAuthorizedError(EngagementError):
    """A stage gate names a designated approver who holds no workspace authority.

    SPEC.md sections 4 and 5: a stage gate is approved by the client-designated
    authority, and an agent cannot confer human approval upon itself. A gate whose
    ``approver`` is absent, or names an actor who is not a named authority on the
    client workspace, cannot be approved on behalf of that client (SPEC.md
    section 11: the aggregate never invents a human authority).
    """


class StageOwnerNotAuthorizedError(EngagementError):
    """A stage gate decision names an assigned work owner who holds no authority.

    SPEC.md sections 1, 3 and 4: every output has an owner, a stage completion
    records an assigned work owner and a due date, and the production view must
    answer "who is accountable" for a stage. An assigned work owner who is not a
    named authority on the client workspace cannot be accountable for the stage,
    so the durable decision would show an owner who does not exist on the client
    (SPEC.md section 11: the aggregate never invents a human authority).
    """


class GateAuthorRequiredError(EngagementError):
    """A stage gate recording path was given a gate with no named author.

    SPEC.md sections 3, 4 and 5: approval pins the proposed version, and the
    author cannot impersonate the approver. The stage 0 recording path issues one
    version-specific approval request per required asset on behalf of the gate's
    author, so a gate that names no author cannot establish who requested the
    client's approval.
    """


class NotStageZeroGateError(EngagementError):
    """A stage 0 recording path was handed a gate for another stage.

    SPEC.md section 4 makes stage 0 "Intake" the first production checkpoint.
    The stage 0 recording path pins and approves only the canonical stage 0 gate;
    a gate for another stage must be recorded by that stage's own path so the
    wrong asset package is never approved under the stage 0 rubric.
    """


class StageRunNotStageZeroError(EngagementError):
    """A stage 0 closure was handed a StageRun for another stage or template.

    SPEC.md sections 3 and 4 make a StageRun track one stage of one versioned
    template. Completing a stage 0 gate must close the matching stage 0 run for
    the same template version, so a run for another stage or version cannot be
    closed by the stage 0 path and left showing verified progress the run does
    not represent.
    """


class StageRunNotCompletableError(EngagementError):
    """A stage 0 closure was handed a StageRun whose state cannot complete.

    SPEC.md section 4 rejects illegal transitions rather than silently coercing
    state: a stage reaches COMPLETE only from an active Working or In Review run,
    never from Not Started, Changes Required, Blocked, Waived, Complete or
    Superseded. A run that cannot complete must not cause the gate decision to be
    recorded first, so the ledger and the stage status cannot drift.
    """


class UnsourcedIntakeEvidenceError(EngagementError):
    """A stage 0 intake asset was asked to use unsourced or foreign evidence.

    SPEC.md sections 1 and 4: every output has a source, and previously approved
    client assets satisfy a gate only after source, authority, version and fit are
    checked. An intake asset's evidence must be a known, directly sourced
    Knowledge claim of the same client; an unsourced, merely derived or proposed,
    or foreign claim cannot support it.
    """
