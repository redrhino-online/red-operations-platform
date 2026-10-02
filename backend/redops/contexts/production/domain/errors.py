"""Named domain errors for the Production bounded context (pure domain)."""

from __future__ import annotations


class ProductionError(Exception):
    """Base class for production domain rule violations."""


class InvalidBuildError(ProductionError, ValueError):
    """A BuildObject was constructed or changed in a way the invariant forbids."""


class IllegalBuildTransitionError(ProductionError):
    """A BuildObject was asked to move between states its lifecycle forbids."""
