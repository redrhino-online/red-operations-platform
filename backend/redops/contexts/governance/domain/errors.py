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
