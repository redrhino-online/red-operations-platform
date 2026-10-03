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


class InvalidFunnelIntegrationPackageError(ExecutionError, ValueError):
    """A stage 8 reviewed asset package was built without identity, version or completion.

    SPEC.md sections 3 and 4: a passing stage 8 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 8 ``FunnelIntegration`` is
    projected onto the thirteen canonical asset kinds with a positive integer
    version. A package that leaves its identity or the funnel version unspecified
    cannot be represented as exact gate evidence. The same error is raised when
    the funnel has not passed "Funnel Complete", because its thirteen kinds would
    then be pinned without a completed funnel to own them (a missing asset
    prevents gate completion and a waiver never makes an absent asset appear
    present).
    """


class FunnelIntegrationPackageTenantBoundaryError(ExecutionError):
    """A stage 8 reviewed asset package mixed in a funnel from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``FunnelIntegration`` projected onto a workspace's stage 8 gate package must
    belong to that workspace's tenant. A cross-tenant stage 8 funnel cannot be
    pinned as this client's gate evidence.
    """


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


class InvalidLaunchQAPackageError(LaunchQAError, ValueError):
    """A stage 9 reviewed asset package was built without identity, version or readiness.

    SPEC.md sections 3 and 4: a passing stage 9 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 9 ``LaunchQA`` is projected onto
    the sixteen canonical asset kinds with a positive integer version. A package
    that leaves its identity or the QA version unspecified cannot be represented as
    exact gate evidence. The same error is raised when the QA has not passed
    "Launch Approved", because its sixteen kinds would then be pinned without an
    authorization to begin traffic to own them (a missing asset prevents gate
    completion and a waiver never makes an absent asset appear present).
    """


class LaunchQAPackageTenantBoundaryError(LaunchQAError):
    """A stage 9 reviewed asset package mixed in launch QA from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``LaunchQA`` projected onto a workspace's stage 9 gate package must belong to
    that workspace's tenant. A cross-tenant stage 9 QA cannot be pinned as this
    client's gate evidence.
    """


class PerformanceBaselineError(ExecutionError):
    """Base class for stage 10 performance baseline rule violations."""


class InvalidPerformanceBaselineError(PerformanceBaselineError, ValueError):
    """A PerformanceBaseline or its value objects violate an invariant."""


class PerformanceBaselineDependencyError(PerformanceBaselineError):
    """A baseline is not grounded on a ready-for-traffic stage 9 launch QA."""


class PerformanceBaselineIncompleteError(PerformanceBaselineError):
    """Observations do not satisfy "Performance Baseline Established"."""


class PerformanceClaimError(PerformanceBaselineError):
    """Base class for observation-versus-causal claim rule violations."""


class InvalidPerformanceClaimError(PerformanceClaimError, ValueError):
    """A PerformanceClaim value object violates an invariant."""


class PerformanceClaimSupportError(PerformanceClaimError):
    """A causal claim lacks an established baseline or an adequate sample."""
