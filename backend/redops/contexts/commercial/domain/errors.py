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


class InvalidCurrencyInventoryError(CommercialError, ValueError):
    """A stage 2 currency inventory was built without a category or currencies.

    SPEC.md section 4, stage 2 "Position": the required asset package names the
    category, the currency inventory and the primary currency. The reference model
    canon (SPEC.md section 12.3: stage 2 uses canon files 04, 05 and 06) has the
    currency calculator leave the general category behind and list every currency
    the offer can increase or decrease. An inventory that names no category or no
    currency on either side cannot record that reach, so it cannot be a reviewed
    stage 2 asset.
    """


class InvalidPositioningDecisionError(CommercialError, ValueError):
    """A stage 2 positioning decision was built without a required dimension.

    SPEC.md section 4, stage 2 "Position": the required asset package names the
    horizon, qualifications, transformation statement and core problem. The canon
    (files 05 and 06) frames this as the four step problem, prescription and
    prognosis with a stated acceptance and rejection line. A decision that leaves
    the problem, the transformation, the horizon or the acceptance line
    unspecified cannot be represented as a reviewed stage 2 asset.
    """


class InvalidMillionDollarMessageError(CommercialError, ValueError):
    """A stage 2 million dollar message was built without a formula component.

    SPEC.md section 4, stage 2: the required asset package ends with the Million
    Dollar Message. The canon (file 06) states the formula as a single avatar
    times one currency with a metric and a timeline minus the pain removed. A
    message that leaves the avatar, currency, metric, timeline or pain
    unspecified cannot be represented as a complete stage 2 asset.
    """


class InvalidCurrencyPackageError(CommercialError, ValueError):
    """A stage 2 reviewed asset package was built without identity or version.

    SPEC.md sections 3 and 4: a passing stage 2 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 2 assets are projected onto
    the ten canonical asset kinds with a positive integer version each. A package
    that leaves its identity or an asset version unspecified cannot be
    represented as exact gate evidence.
    """


class CurrencyTenantBoundaryError(CommercialError):
    """A stage 2 reviewed asset package mixed in a value from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    currency inventory, positioning decision, primary currency and million dollar
    message projected onto a workspace's stage 2 gate package must all belong to
    that workspace's tenant. A cross-tenant stage 2 value cannot be pinned as this
    client's gate evidence.
    """


class InvalidDiagnosticPackageError(CommercialError, ValueError):
    """A stage 3 reviewed asset package was built without identity or version.

    SPEC.md sections 3 and 4: a passing stage 3 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 3 ``DiagnosticModel`` is
    projected onto the ten canonical asset kinds with a positive integer version.
    A package that leaves its identity or the model version unspecified cannot be
    represented as exact gate evidence.
    """


class DiagnosticTenantBoundaryError(CommercialError):
    """A stage 3 reviewed asset package mixed in a model from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``DiagnosticModel`` projected onto a workspace's stage 3 gate package must
    belong to that workspace's tenant. A cross-tenant stage 3 model cannot be
    pinned as this client's gate evidence.
    """


class InvalidSignaturePackageError(CommercialError, ValueError):
    """A stage 4 reviewed asset package was built without identity or version.

    SPEC.md sections 3 and 4: a passing stage 4 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 4 ``SignatureSolution`` is
    projected onto the twelve canonical asset kinds with a positive integer
    version. A package that leaves its identity or the solution version
    unspecified cannot be represented as exact gate evidence.
    """


class SignatureTenantBoundaryError(CommercialError):
    """A stage 4 reviewed asset package mixed in a solution from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``SignatureSolution`` projected onto a workspace's stage 4 gate package must
    belong to that workspace's tenant. A cross-tenant stage 4 solution cannot be
    pinned as this client's gate evidence.
    """


class InvalidOfferPackageError(CommercialError, ValueError):
    """A stage 5 reviewed asset package was built without identity or version.

    SPEC.md sections 3 and 4: a passing stage 5 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 5 ``DeliverySpecification`` is
    projected onto the twelve canonical asset kinds with a positive integer
    version. A package that leaves its identity or the delivery version
    unspecified cannot be represented as exact gate evidence.
    """


class OfferTenantBoundaryError(CommercialError):
    """A stage 5 reviewed asset package mixed in a delivery from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``DeliverySpecification`` projected onto a workspace's stage 5 gate package
    must belong to that workspace's tenant. A cross-tenant stage 5 delivery
    cannot be pinned as this client's gate evidence.
    """


class InvalidCampaignMessagePackageError(CommercialError, ValueError):
    """A stage 6 reviewed asset package was built without identity or version.

    SPEC.md sections 3 and 4: a passing stage 6 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 6 ``CampaignMessage`` is
    projected onto the twelve canonical asset kinds with a positive integer
    version. A package that leaves its identity or the message version
    unspecified cannot be represented as exact gate evidence.
    """


class CampaignMessageTenantBoundaryError(CommercialError):
    """A stage 6 reviewed asset package mixed in a message from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``CampaignMessage`` projected onto a workspace's stage 6 gate package must
    belong to that workspace's tenant. A cross-tenant stage 6 message cannot be
    pinned as this client's gate evidence.
    """

