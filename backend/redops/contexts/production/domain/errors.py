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
