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
