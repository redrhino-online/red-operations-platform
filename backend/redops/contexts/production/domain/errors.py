"""Named domain errors for the Production bounded context (pure domain)."""

from __future__ import annotations


class ProductionError(Exception):
    """Base class for production domain rule violations."""


class InvalidBuildError(ProductionError, ValueError):
    """A BuildObject was constructed or changed in a way the invariant forbids."""


class IllegalBuildTransitionError(ProductionError):
    """A BuildObject was asked to move between states its lifecycle forbids."""


class InvalidAuthorityAmplifierError(ProductionError, ValueError):
    """An AuthorityAmplifier was constructed or changed against its invariant."""


class AuthorityAmplifierDependencyError(ProductionError):
    """An AuthorityAmplifier is not grounded on an approved dependency."""


class AuthorityAmplifierApprovalOrderError(ProductionError):
    """A creative approval was attempted before the script was approved."""


class UnsupportedProofError(ProductionError):
    """Proof offered in a script is not a known, directly sourced claim."""


class InvalidAuthorityAmplifierPackageError(ProductionError, ValueError):
    """A stage 7 reviewed asset package was built without identity or version.

    SPEC.md sections 3 and 4: a passing stage 7 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 7 ``AuthorityAmplifier`` is
    projected onto the nine canonical asset kinds with a positive integer
    version. A package that leaves its identity or the amplifier version
    unspecified cannot be represented as exact gate evidence. The same error is
    raised when the amplifier has no visual package, because its eight video
    kinds would then be pinned without an asset to own them (a missing asset
    prevents gate completion and a waiver never makes an absent asset appear
    present).
    """


class AuthorityAmplifierTenantBoundaryError(ProductionError):
    """A stage 7 reviewed asset package mixed in an amplifier from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``AuthorityAmplifier`` projected onto a workspace's stage 7 gate package must
    belong to that workspace's tenant. A cross-tenant stage 7 amplifier cannot be
    pinned as this client's gate evidence.
    """


class AuthorityAmplifierReadinessError(ProductionError):
    """An approved amplifier store was asked to hold an unapproved amplifier.

    SPEC.md sections 3 and 4: the stage 8 to 10 gates ground on the exact stage 7
    ``AuthorityAmplifier`` that received creative acceptance at "Authority
    Amplifier Approved". An amplifier that has not passed that checkpoint cannot
    be stored as the dependency a later gate resolves.
    """


class AuthorityAmplifierVersionConflictError(ProductionError):
    """A stored amplifier id was re-stated with different content.

    SPEC.md sections 3 and 4: a passing gate pins the exact approved asset
    version, and a previous approved version stays historically identifiable. The
    store is append-only per ``(tenant_id, amplifier_id)``: an approved amplifier
    is immutable, and a change must be a new revision under a new id.
    """


class AuthorityAmplifierVersionTenantBoundaryError(ProductionError):
    """A client's approved amplifier was read or written without a tenant.

    SPEC.md sections 3 and 9 make an amplifier a client resource that must carry
    its tenant on every command and query; storing or resolving one without a
    client would either leak across clients or create an orphaned record.
    """


class InvalidAuthorityVideoKitError(ProductionError, ValueError):
    """An AuthorityVideoKit was constructed or changed against its invariant.

    SPEC.md section 12.5 records the authority-video kit as a canon gap and the
    implementation plan's canon gap backlog item G2 names a typed artifact. A kit
    that leaves its identity, flagship title or flagship action blank, or that
    carries a non-typed step video or a non-integer duration, cannot be
    represented as the prescribed 10-pack.
    """


class AuthorityVideoKitDependencyError(ProductionError):
    """An AuthorityVideoKit is not grounded on a typed, produced dependency.

    SPEC.md section 4, stage 7: the script and its supported claims pass review
    before any visual or video production, and the canon gate checks the script
    before the slides are made. The 10-pack is cut from the produced stage 7
    ``AuthorityAmplifier`` and names the nine steps of the stage 4
    ``SignatureSolution``, so a kit without a typed amplifier that has produced
    its video, or without a typed solution, or with a step video whose step the
    solution does not name, cannot be built.
    """


class AuthorityVideoKitTenantBoundaryError(ProductionError):
    """An AuthorityVideoKit mixed in an amplifier, solution or video from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    stage 7 amplifier, the stage 4 solution and every step video a kit is built
    from must belong to the kit's tenant. A cross-tenant dependency cannot be
    represented as this client's 10-pack.
    """


class AuthorityVideoKitFormatError(ProductionError):
    """An AuthorityVideoKit breaks the canon's 10-pack shape.

    The canon (files 13-18; High Ticket Funnels 05, 06, 08) fixes one flagship
    video of 8 to 20 minutes plus exactly nine step videos, one per signature
    solution step, each no longer than the flagship. A kit that breaks that shape
    cannot be represented as the prescribed pack.
    """


class AuthorityVideoKitObservationError(ProductionError):
    """An AuthorityVideoKit was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The kit
    describes the videos that will be produced, while any measured watch time,
    opt-in rate or booked calls are separate observations, so a kit is never an
    observation.
    """


class BuildTenantBoundaryError(ProductionError):
    """A client's BuildObject was read or written without a tenant.

    SPEC.md sections 3 and 9 make a build a client resource that must carry its
    tenant on every command and query; storing, listing or resolving one without a
    client would either leak across clients or create an orphaned record.
    """


class BuildObjectVersionConflictError(ProductionError):
    """A build mutation carried a stale expected version (SPEC.md section 7).

    SPEC.md section 7: "optimistic version checking returns conflict on stale
    updates." A BuildObject is a live aggregate (SPEC.md section 4), so a caller
    that read version N and writes after another writer advanced the build is
    refused rather than silently overwriting the newer state. The conflict is a
    named error, never a partial write.
    """


class BuildConfigurationError(RuntimeError):
    """The BuildObject store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept a
    build that vanishes on restart, so a missing psycopg driver is a configuration
    error rather than a degraded mode (SPEC.md sections 3 and 9).
    """
