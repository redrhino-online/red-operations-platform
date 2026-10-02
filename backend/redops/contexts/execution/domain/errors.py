"""Named domain errors for the Execution bounded context (pure domain)."""

from __future__ import annotations


class ExecutionError(Exception):
    """Base class for execution domain rule violations."""


class InvalidFunnelError(ExecutionError, ValueError):
    """A FunnelIntegration or its value objects violate an invariant."""


class FunnelDependencyError(ExecutionError):
    """A funnel is not grounded on an approved stage 7 dependency."""


class FunnelIncompleteError(ExecutionError):
    """The prospect path does not satisfy the "Funnel Complete" checkpoint."""


class LaunchQAError(ExecutionError):
    """Base class for stage 9 launch QA rule violations."""


class InvalidLaunchQAError(LaunchQAError, ValueError):
    """A LaunchQA or its value objects violate an invariant."""


class LaunchQADependencyError(LaunchQAError):
    """A launch QA is not grounded on a completed stage 8 funnel."""


class LaunchQAIncompleteError(LaunchQAError):
    """Checks do not satisfy the "Launch Approved" checkpoint."""


class LaunchQAAuthorityError(LaunchQAError):
    """Traffic was not authorized by the designated human authority."""
