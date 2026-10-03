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


class InvalidCampaignMessageError(CommercialError, ValueError):
    """A stage 6 campaign message was built without its required identity or content.

    SPEC.md section 4, stage 6 "Message": the required asset package is the
    promise, problem hierarchy, desired outcome, proof and objections, story,
    method explanation, CTA, lead magnet, hook, angles, landing message and
    Authority Amplifier outline. A message that leaves any of these unspecified
    cannot be represented as an approvable campaign message.
    """


class CampaignMessageDependencyError(CommercialError):
    """A campaign message pinned an upstream asset from another tenant.

    SPEC.md section 3: every tenant resource belongs to exactly one client. A
    stage 6 message is grounded on the tenant's approved stage 5 offer, so it
    cannot be built on another client's offer.
    """


class CampaignMessageAlignmentError(CommercialError):
    """A stage 6 campaign message did not agree with its approved stage 5 offer.

    SPEC.md section 4, stage 6 and its "Campaign Message Approved" checkpoint:
    the avatar, currency, problem, promise, method, product and CTA must agree,
    and the message is grounded on the approved stage 5 offer. A message that
    conflicts with the locked offer or the approved method it references cannot
    be approved.
    """


class InvalidAvatarProfileError(CommercialError, ValueError):
    """A stage 1 avatar profile was built without a recognizability dimension.

    SPEC.md section 4, stage 1 "Diagnose": the required asset package names the
    avatar with demographics and psychographics, pains, goals, consequences of
    inaction, awareness, customer evidence and voice notes. An avatar that
    leaves any of these unspecified cannot be represented as a lockable avatar.
    """


class AvatarLockedError(CommercialError):
    """A stage 1 avatar was asked to lock on unsourced or foreign evidence.

    SPEC.md sections 1 and 4: every output has a source, and the stage 1
    "Avatar Locked" checkpoint requires customer evidence. Evidence that is not
    a known, directly sourced claim of the same client cannot support the lock.
    """


class InvalidBusinessSnapshotError(CommercialError, ValueError):
    """A stage 1 business snapshot was built without a current-state dimension.

    SPEC.md section 4, stage 1 "Diagnose": the required asset package names the
    business snapshot. A snapshot that leaves the current business model, offers,
    lead sources, constraints or narrative unspecified cannot be represented as a
    diagnosable asset. SPEC.md section 1 also requires every output to have a
    source, so the snapshot records the claim ids that evidence it.
    """


class InvalidOfferFunnelAuditError(CommercialError, ValueError):
    """A stage 1 offer and funnel audit was built without an audit dimension.

    SPEC.md section 4, stage 1 "Diagnose": the required asset package names the
    offer and funnel audit. An audit that leaves the offer findings, funnel steps,
    conversion evidence, gaps or narrative unspecified cannot be represented as a
    diagnosable asset. SPEC.md section 1 also requires every output to have a
    source, so the audit records the claim ids that evidence it.
    """


class UnsourcedDiagnosisEvidenceError(CommercialError):
    """A stage 1 diagnosis asset was asked to use unsourced or foreign evidence.

    SPEC.md sections 1 and 4: every output has a source, so the business snapshot
    and the offer and funnel audit must be evidenced by known, directly sourced
    Knowledge claims of the same client. Evidence that is unsourced, merely
    derived or proposed, or belongs to another client cannot support a stage 1
    diagnosis asset. A missing claim cannot be represented as evidence.
    """


class InvalidDiagnosisPackageError(CommercialError, ValueError):
    """A stage 1 diagnosis package was built without an identity or exact version.

    SPEC.md sections 3 and 4: a passing stage 1 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 1 assets are projected onto the
    canonical asset kinds with a positive integer version each. A package that
    leaves its identity or an asset version unspecified cannot be represented as
    exact gate evidence.
    """


class DiagnosisTenantBoundaryError(CommercialError):
    """A stage 1 diagnosis package mixed in a value from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    avatar, business snapshot and offer and funnel audit projected onto a
    workspace's stage 1 gate package must all belong to that workspace's tenant.
    A cross-tenant diagnosis value cannot be pinned as this client's gate evidence.
    """

