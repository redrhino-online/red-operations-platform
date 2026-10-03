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
