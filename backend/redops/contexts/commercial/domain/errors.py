"""Named domain errors for the Commercial Design bounded context (pure domain)."""

from __future__ import annotations


class CommercialError(Exception):
    """Base class for commercial design domain rule violations."""


class InvalidOfferError(CommercialError, ValueError):
    """An OfferVersion was built or changed without its required identity or content."""


class OfferReadinessError(CommercialError):
    """An OfferVersion was asked to be production ready without approved dependencies.

    SPEC.md section 3: production requires approved dependencies. An offer must
    pin an approved method version and intended use before it can proceed.
    """


class OfferDependencyError(CommercialError):
    """An OfferVersion pinned an upstream asset that does not belong to its tenant.

    SPEC.md section 3: every tenant resource belongs to exactly one client. The
    stage 5 delivery specification is grounded on the tenant's locked stage 4
    Signature Solution, so it cannot be pinned across a tenant boundary.
    """


class InvalidDeliverySpecificationError(CommercialError, ValueError):
    """A stage 5 delivery specification was not a complete offer delivery package.

    SPEC.md section 4, stage 5 "Productize" and its "Offer Locked" checkpoint:
    every method step has an action, actor, deliverable, timing and measure, and
    the required asset package also names the delivery model, duration, modules,
    responsibilities, support cadence, stage deliverables, outcome measures,
    pricing and payments, scope, guarantee decision, eligibility and offer stack.
    A missing method step or a step the method does not have cannot be represented
    as an approvable offer.
    """
