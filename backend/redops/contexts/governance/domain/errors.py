"""Named domain errors for the Governance bounded context (pure domain)."""

from __future__ import annotations


class GovernanceError(Exception):
    """Base class for governance domain rule violations."""


class SelfApprovalError(GovernanceError, ValueError):
    """An author was designated as the approver of their own proposal."""


class ApprovalAuthorityError(GovernanceError):
    """An actor without the designated authority attempted to decide an approval."""


class ApprovalExpiredError(GovernanceError):
    """An approval was acted on after its expiry date."""


class IllegalStageTransitionError(GovernanceError):
    """A StageRun was asked to move between statuses its state machine forbids."""


class StageGateNotAcceptedError(GovernanceError):
    """A StageRun was asked to complete without an accepted gate for that stage."""


class InvalidStageTemplateError(GovernanceError, ValueError):
    """A stage 0-10 template was constructed in a way its invariant forbids."""


class UnknownStageError(GovernanceError, ValueError):
    """A gate was requested for a stage the template does not define."""


class AssetPackageMismatchError(GovernanceError, ValueError):
    """A supplied asset package does not match the stage's required asset kinds."""


class VersionlessAssetError(GovernanceError, ValueError):
    """A real stage asset was offered for pinning without an exact positive version.

    A passing gate pins exact asset versions, and approval is version specific
    (SPEC.md sections 3, 4 and 11). An asset that names no positive version
    cannot be pinned as exact evidence, so it is refused rather than treated as
    an unversioned asset.
    """


class CrossTenantAssetError(GovernanceError, ValueError):
    """A real stage asset from another tenant was offered as gate evidence.

    SPEC.md section 3 requires every tenant resource to belong to exactly one
    client and every query to be tenant scoped. A gate may pin only assets owned
    by the workspace tenant, so an asset from another client is refused rather
    than silently pinned.
    """


class AmbiguousAssetPackageError(AssetPackageMismatchError):
    """A package pins more than one version of the same asset kind.

    A gate records an exact version per required asset kind. Two versions of one
    kind leave the version at issue ambiguous, so the package is refused instead
    of being treated as an exact pin (SPEC.md sections 3 and 4).
    """


class GateLedgerError(GovernanceError, ValueError):
    """A gate ledger was asked to record a decision its invariants forbid."""


class UnsatisfiedPrerequisiteError(GateLedgerError):
    """A passing decision was recorded while a prerequisite stage had not passed."""


class CheckpointMismatchError(GateLedgerError):
    """A decision named a checkpoint rubric other than the stage's canonical one."""


class PrerequisiteMismatchError(GateLedgerError):
    """A decision named prerequisite stages other than the stage's canonical ones.

    SPEC.md section 4 requires the gate record to persist the stage's
    dependencies for every disposition. The canonical prerequisite graph lives on
    the template, so a decision that omits, adds or substitutes a prerequisite
    would leave the durable record unable to answer "which dependency blocks
    work" (SPEC.md section 4).
    """


class GateDecisionError(GovernanceError, ValueError):
    """A gate decision was recorded in a way its invariant forbids.

    Raised when a passing decision omits the pinned evidence, reviewer or
    intended scope, when a waiver has no risk owner, or when an approval is
    recorded for a gate that is not approvable.
    """


class UnapprovedAssetError(GateDecisionError):
    """A passing gate decision pinned an asset version with no covering approval.

    Passing a gate requires a recorded, version-specific, in-scope, unexpired
    approval for every pinned asset. A self-declared approved set is not
    evidence of approval (SPEC.md sections 3, 4 and 11).
    """


class ProductionViewError(GovernanceError, ValueError):
    """The production-manager view was built or read in a way its rules forbid.

    SPEC.md section 4 requires the production view to answer for every stage from
    the versioned template and the durable ledger and to separate its eight
    reporting dimensions. A stage view that pins an approved asset outside the
    stage's required package, or a read for a dimension the view does not
    represent, would let the view show evidence or a report the pipeline never
    produced, so it is refused rather than rendered.
    """


class MetricReportingError(ProductionViewError):
    """A METRICS reporting row violates the production-view invariant.

    SPEC.md section 4 separates metrics as one of the eight reporting dimensions
    and the Measurement invariant keeps observations distinct from causal
    conclusions. The METRICS dimension must show a typed figure that was actually
    observed over a closed window, so a row missing its metric identity, window,
    sample, source or recorded date, or one carrying a placeholder figure, is
    refused rather than rendered as verified progress.
    """


class MetricReportingTenantBoundaryError(ProductionViewError):
    """A METRICS reporting row belongs to another client.

    SPEC.md section 3: every tenant resource carries a tenant id and a query is
    tenant scoped. The production view for one client may report only that
    client's metrics, so a row from another tenant is refused rather than
    rendered alongside this engagement's verified progress.
    """
