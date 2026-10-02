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
