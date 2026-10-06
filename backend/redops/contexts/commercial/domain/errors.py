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


class OfferVersionConflictError(CommercialError):
    """An approved offer was re-stated under the same id with different content.

    SPEC.md sections 3 and 4: a passing gate pins the exact approved asset
    version, and a later gate resolves that version rather than re-declaring it.
    An approved offer is immutable under its offer id: a change must be a new
    revision with its own identity, so a same-id request body that differs cannot
    silently replace the offer a prior gate grounded on.
    """


class OfferVersionTenantBoundaryError(CommercialError):
    """A production ready offer was stored or resolved without a client scope.

    SPEC.md sections 3 and 9 make ``tenant_id`` on every tenant resource and
    query a hard invariant. An approved offer is a client resource, so reading or
    writing one without a non-blank tenant would leak across clients or create an
    orphaned record.
    """


class CampaignMessageReadinessError(CommercialError):
    """An approved campaign message store was asked to hold an unapproved message.

    SPEC.md sections 3 and 4: a passing gate pins the exact approved asset
    version, so the stage 6 to 10 gates ground on the stage 6 ``CampaignMessage``
    a prior gate approved at "Campaign Message Approved". A message that has not
    passed that checkpoint cannot be stored as the exact approved version.
    """


class CampaignMessageVersionConflictError(CommercialError):
    """An approved message was re-stated under the same id with different content.

    SPEC.md sections 3 and 4: a passing gate pins the exact approved asset
    version, and a later gate resolves that version rather than re-declaring it.
    An approved message is immutable under its message id: a change must be a new
    revision with its own identity, so a same-id request body that differs cannot
    silently replace the message a prior gate grounded on.
    """


class CampaignMessageVersionTenantBoundaryError(CommercialError):
    """An approved message was stored or resolved without a client scope.

    SPEC.md sections 3 and 9 make ``tenant_id`` on every tenant resource and
    query a hard invariant. An approved message is a client resource, so reading
    or writing one without a non-blank tenant would leak across clients or create
    an orphaned record.
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


class InvalidNurtureError(CommercialError, ValueError):
    """A follow-up and nurture message was built without its required content.

    SPEC.md section 12.3 places the follow-up and nurture lifecycle after stage 10
    and section 12.5 records it as a canon gap, shaped by the canon's Signature
    Solution Series, 5P messaging and re-engagement material (canon files 15, 24,
    33 and 34). A nurture message names its prospect state, its 5P modality, the
    Signature Solution step it derives from, a subject and a purpose, so a blank
    or untyped message cannot be represented as follow-up content.
    """


class NurtureTenantBoundaryError(CommercialError):
    """A nurture message or plan mixed in an asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    nurture message, its sequence, or the Signature Solution the plan derives
    content from cannot cross a tenant boundary.
    """


class NurtureDependencyError(CommercialError):
    """A nurture message was not grounded on the approved Signature Solution.

    The canon's Signature Solution Series takes each step of the Signature
    Solution and turns it into follow-up content (canon file 15), so a plan must
    be grounded on a same-tenant Signature Solution and every message must address
    one of that solution's named steps. A message about a step the method does not
    have, or a sequence the plan does not declare, cannot be represented as
    follow-up content.
    """


class NurtureSequenceError(CommercialError):
    """A nurture sequence was built out of the canon's messaging discipline.

    The canon's 5P framework asks one question with the "ping" modality and asks
    it one at a time (canon files 24 and 33), and re-engages non-openers by
    resending with different headlines rather than repeating one identical message
    (canon file 24). A sequence that mixes prospect states, duplicates a message,
    asks no question with a ping, or re-engages non-openers with a single or
    repeated subject violates that discipline.
    """


class NurtureObservationError(CommercialError):
    """A nurture plan was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. A nurture
    plan is the follow-up content that will run, while any measured movement stays
    a separate observation, so a plan is never an observation.
    """


class InvalidMarketAwarenessMapError(CommercialError, ValueError):
    """A stage 1 market awareness map was built without its required content.

    SPEC.md section 12.3 maps the market awareness levels to stage 1 and section
    12.5 records the positioning and decision tools as a canon gap, shaped by the
    canon's five levels of market awareness (canon file 04): completely unaware,
    problem aware, solution aware, product aware and most aware. The map names the
    level the market currently sits at, the research evidence that places it
    there, and what a message must supply at that level, so a blank identity, an
    untyped level, or a map with no evidence or message requirements cannot be
    represented as stage 1 awareness-map evidence.
    """


class MarketAwarenessTargetingError(CommercialError):
    """A market awareness map was asked to target a market it cannot reach.

    The canon places the completely unaware outside the initial target (canon
    file 04: "which is who we definitely do not want to sell to initially") and
    treats retargeting as a step further down the funnel, so a retarget level must
    be more aware than the primary level. A map that targets the unprepared or
    the already-aware with the same message cannot be represented as a defensible
    awareness position (SPEC.md section 4, stage 1 "Avatar Locked").
    """


class InvalidTargetMarketMatchmakerError(CommercialError, ValueError):
    """A target market candidate or match was built without its required content.

    SPEC.md section 12.5 records the positioning and decision tools as a canon
    gap. The canon's target market matchmaker takes two or three candidate
    markets and narrows them to the one to serve now, judging each on being
    passionate to help, a clear problem the offer solves, real profit,
    reachability and a clear point A to point B pathway (canon file 00). A
    candidate missing a criterion, a match with fewer than two candidates, a
    duplicate candidate or a selected market that is not among the candidates
    cannot be represented as a target market decision.
    """


class TargetMarketTenantBoundaryError(CommercialError):
    """A target market match mixed in an asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. The
    awareness position the chosen market is placed against cannot cross a tenant
    boundary, so a match cannot cite another client's awareness map.
    """


class TargetMarketMatchError(CommercialError):
    """A target market match was asked to serve a market it cannot serve now.

    The canon narrows the candidate markets to the one to serve now (canon file
    00), and its awareness research (canon file 04) places the completely
    unaware outside the initial target. A match whose chosen market sits at the
    completely unaware level cannot be served as the current target market
    (SPEC.md sections 4 and 12.5).
    """


class TargetMarketObservationError(CommercialError):
    """A target market match was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The match is
    a planning decision about which market to serve, while any measured movement
    stays a separate observation, so a match is never an observation.
    """


class InvalidFunnelFinderError(CommercialError, ValueError):
    """A funnel profile or finder was built without its required content.

    SPEC.md section 12.5 records the positioning and decision tools as a canon
    gap. The canon's funnel finder decides which marketing system or funnel to
    deploy from a business's technical level, experience, offer price and
    business model (canon files 13 and 14), choosing one of the funnel types the
    canon trains its community on (liquid, local, CAC, webinar, quiz, launch). A
    profile missing a canon factor, or a finder with fewer than two considered
    types, a duplicate type, an untyped selection or a selected type that is not
    among the considered types cannot be represented as a funnel decision.
    """


class FunnelFinderTenantBoundaryError(CommercialError):
    """A funnel finder mixed in a profile from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. The
    business profile the funnel is selected for cannot cross a tenant boundary,
    so a finder cannot cite another client's funnel profile.
    """


class FunnelFitError(CommercialError):
    """A funnel finder chose a funnel type that does not fit the offer price.

    The canon states that a sales-call funnel does not fit a low-ticket offer
    ("it doesn't make sense to do a sales call to sell a product for $5") and
    that a quick self-serve funnel does not fit a high-ticket consulting offer
    ("it doesn't make sense to try to sell a $20,000 consulting package online
    with a quick video sales letter") (canon file 13). A selection that pairs
    those must be refused (SPEC.md sections 4 and 12.5).
    """


class FunnelFinderObservationError(CommercialError):
    """A funnel finder was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The finder
    is a planning decision about which funnel to deploy, while any measured
    movement stays a separate observation, so a finder is never an observation.
    """


class InvalidContentRoadmapError(CommercialError, ValueError):
    """A content topic or roadmap was built without its required content.

    SPEC.md section 12.3 places the Content Roadmap with stage 6 and section
    12.5 records the audience-building and content flywheel as a canon gap
    shaped by the canon's Content Blitz (canon files 25-31). A content topic
    names the Signature Solution step it derives from, the audience question it
    answers, the channels it is published to and the Authority Amplifier script
    it follows; a roadmap names its owner, the same-tenant Signature Solution it
    is mapped from, and at least one topic. A blank or untyped topic or roadmap
    cannot be represented as a content plan.
    """


class ContentRoadmapTenantBoundaryError(CommercialError):
    """A content topic or roadmap mixed in an asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    content topic, its roadmap, or the Signature Solution the roadmap maps from
    cannot cross a tenant boundary.
    """


class ContentRoadmapDependencyError(CommercialError):
    """A content topic was not grounded on the mapped Signature Solution.

    The canon builds the content roadmap by taking each step of the Signature
    Solution and brainstorming the FAQs and questions the audience asks about it
    (canon files 26 and 27), so a roadmap must be grounded on a same-tenant
    stage 4 Signature Solution and every topic must address one of that
    solution's named steps. A topic about a step the method does not have cannot
    be represented as part of the content plan.
    """


class ContentRoadmapFormatError(CommercialError):
    """A content topic broke the canon's content format discipline.

    The canon asks every piece of audience-building content to follow the
    Authority Amplifier script format (canon file 26), whose order is Promise,
    Proof, Problems, Steps, Context, Action (SPEC.md section 4, stage 7), and it
    does not repeat a channel for one piece of content. A topic whose script
    beats are missing, reordered or duplicated, or whose channels are duplicated,
    violates that discipline.
    """


class ContentDistributionError(CommercialError):
    """A content topic was not published widely enough.

    The canon requires each piece of content to be published "to YouTube,
    Facebook and blog at a minimum" (canon file 29) and warns that posting an
    asset in only one place loses most of its equity (canon file 31), so a topic
    that does not reach all of the canon's minimum publish channels cannot be
    represented as an evergreen content plan (SPEC.md sections 4 and 12.5).
    """


class ContentRoadmapObservationError(CommercialError):
    """A content roadmap was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. A content
    roadmap is the content that will be produced and published, while any
    measured movement stays a separate observation, so a roadmap is never an
    observation.
    """


class InvalidContentSyndicationError(CommercialError, ValueError):
    """A content syndication plan or one of its parts was incomplete.

    SPEC.md section 12.5 records the content syndication and recycling schedule
    as the remaining delivery asset of the audience-building and content flywheel
    canon gap, shaped by the canon's Content Blitz publish, promote and syndicate
    training (canon files 29, 30 and 31). A syndication names the roadmap topic it
    distributes, at least one typed channel with a per-channel cadence, at least
    one recycled derivative format and a positive daily promotion budget; a plan
    names its owner, the same-tenant Content Roadmap it distributes and at least
    one syndication.
    """


class ContentSyndicationDependencyError(CommercialError):
    """A content syndication was not grounded on the mapped Content Roadmap.

    The canon syndicates the content assets the roadmap already planned, so a
    plan must be grounded on a same-tenant Content Roadmap and every syndication
    must distribute one of that roadmap's named topics. A syndication of a topic
    the roadmap does not have cannot be represented as part of the schedule
    (SPEC.md section 3).
    """


class ContentSyndicationTenantBoundaryError(CommercialError):
    """A content syndication plan mixed in an asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    syndication plan and the Content Roadmap it distributes cannot cross a tenant
    boundary.
    """


class ContentSyndicationFormatError(CommercialError):
    """A content syndication broke the canon's distribution discipline.

    The canon distributes one piece of content once per channel and recycles it
    into distinct derivative formats (canon file 31), so a syndication that
    repeats a channel or repeats a recycled format cannot be represented as the
    schedule.
    """


class ContentSyndicationError(CommercialError):
    """A content syndication plan left an asset in one place.

    The canon syndicates every asset "anywhere you can reach your audience" and
    warns that posting an asset once "you're losing 99% of the equity of the
    asset you've created" (canon file 31). A plan that posts an asset to a single
    channel, or only to borrowed social channels without an owned audience
    channel, cannot build the retargetable audience the canon's content flywheel
    depends on (SPEC.md sections 4 and 12.5).
    """


class ContentSyndicationObservationError(CommercialError):
    """A content syndication plan was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. A syndication
    plan is the distribution that will happen, while any measured movement stays
    a separate observation, so a plan is never an observation.
    """


class InvalidContentCrusherError(CommercialError, ValueError):
    """A content crusher was built without its required topic, promise or beats.

    SPEC.md section 12.5 records the Content Crusher as part of the
    audience-building and content flywheel canon gap, shaped by the canon's
    Content Crusher framework (canon files 12, 16 and 32): each piece of content
    is outlined with a topic, a title, a promise carrying a metric and a timeline,
    the customer's frustrations and goal, a visual model, a metaphor, the context,
    the steps, a story, a choice and the next action. A crusher missing any
    required beat cannot be represented as a world class content outline.
    """


class ContentCrusherDependencyError(CommercialError):
    """A content crusher was not grounded on the mapped Content Roadmap.

    The canon never creates a piece of content that does not live in the
    signature solution (canon file 28) and outlines each roadmap topic on the
    same Content Crusher framework (canon file 32), so a crusher must be
    grounded on a same-tenant Content Roadmap and outline one of that roadmap's
    named topics using the solution's own steps.
    """


class ContentCrusherTenantBoundaryError(CommercialError):
    """A content crusher mixed in an asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    crusher and the Content Roadmap it outlines cannot cross a tenant boundary.
    """


class ContentCrusherObservationError(CommercialError):
    """A content crusher was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. A crusher is
    the content that will be produced, while any measured movement stays a
    separate observation, so a crusher is never an observation.
    """


class InvalidProductProgramError(CommercialError, ValueError):
    """A product program or one of its modules was built without its content.

    SPEC.md section 4, stage 5 "Productize" and its "Offer Locked" checkpoint
    need the delivery model, duration and pricing named, and SPEC.md section 12.3
    shapes stage 5 with the canon's Perfect Product training (canon files 11 and
    12). The canon chooses one of the product matrix's seven business models,
    structures the offer over six to twelve weeks and delivers it on the Monday
    training and Thursday coaching cadence. A module missing its step, outcome or
    deliverable, or a program with a blank identity or owner, an untyped model, a
    duration outside six to twelve weeks, a cadence other than Monday and
    Thursday, a duplicate module or a module that names no method step cannot be
    represented as a productized offer.
    """


class ProductProgramPricingError(CommercialError):
    """A product program was priced against time and materials.

    The canon prices the program "based on outcomes and value to your clients,
    not time and materials" (canon file 11), because charging for time caps the
    business and attracts clients who are not invested in the result. A program
    whose pricing basis is time and materials cannot be represented as a canon-
    shaped offer (SPEC.md sections 4 and 12.3).
    """


class ProductProgramDependencyError(CommercialError):
    """A product program was not grounded on the locked Signature Solution.

    SPEC.md section 12.3 shapes stage 5 with the canon's Perfect Product training
    (canon files 11 and 12), which structures the program as one module per step
    of the signature solution: "break your signature solution into nine clear
    modules" (canon file 12). A program must be grounded on a same-tenant stage 4
    ``SignatureSolution`` and every module must teach one of that solution's
    named steps. A module for a step the method does not have cannot be
    represented as part of the offer.
    """


class ProductProgramTenantBoundaryError(CommercialError):
    """A product program mixed in an asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    program, its modules and the Signature Solution it is grounded on cannot
    cross a tenant boundary.
    """


class ProductProgramObservationError(CommercialError):
    """A product program was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The program
    describes the delivery model and pricing that will run, while any measured
    movement stays a separate observation, so a program is never an observation.
    """


class InvalidAudienceReachError(CommercialError, ValueError):
    """An audience reach estimate was built without its required research content.

    SPEC.md section 12.3 maps the audience sizing research (Facebook Audience
    Insights and LinkedIn search) to stage 1 "Diagnose", and the canon's market
    gate is that "the market is big enough, reachable" (canon files 02 and 03).
    The estimate names the research platform, where and who the audience is, the
    interest signals that stand in for the avatar, and an estimated reachable
    audience size. A blank identity, owner or research note, an untyped platform
    or audience, a non-positive reach or a duplicate interest signal cannot be
    represented as stage 1 audience sizing evidence.
    """


class AudienceReachObservationError(CommercialError):
    """An audience reach estimate was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The canon
    calls the sizing a rough first-pass litmus test that will change (canon file
    02: "it doesn't have to be perfect. You'll probably change it"), so the
    estimate is a research input, not a measured result.
    """


class MarketReachError(CommercialError):
    """A market reach estimate failed the canon's "big and reachable" check.

    The canon's market gate is that "the market is big enough, reachable" and
    that the market is confirmed across more than one network so you know you are
    "climbing the right mountain" (canon files 02 and 03). An estimate below the
    caller's minimum viable audience, or a single-platform litmus, cannot be
    represented as a defensible stage 1 market reach check.
    """


class MarketReachBoundaryError(CommercialError):
    """A market reach confirmation mixed estimates that do not size one market.

    SPEC.md sections 3 and 9 make ``tenant_id`` on every tenant resource and
    query a hard invariant, and the canon confirms one market across more than
    one network so you know you are "climbing the right mountain" (canon files
    02 and 03). A confirmation whose estimates span more than one client, or that
    includes something that is not a typed estimate, cannot be represented as one
    market reach check.
    """



class InvalidContentPlanError(CommercialError, ValueError):
    """A content plan or one of its ideas left a required field unstated.

    SPEC.md section 12.5 records the Extract motion (the pre-content plan) as a
    canon gap and the implementation plan's bounded slice names a pure-domain
    ``ContentPlan`` grounded on the same-tenant stage 4 Signature Solution. A
    blank identity, owner, theme, idea prompt or channel set cannot be
    represented as the content plan that feeds stage 6 and stage 10 content
    operations.
    """


class ContentPlanDependencyError(CommercialError):
    """A content plan depended on a method or idea it cannot map from.

    The canon's first content rule is that content never leaves the method: "we
    never create a piece of content that doesn't live in the signature solution"
    (canon file 28), and the plan is built by brainstorming the questions for each
    step of the Signature Solution (canon file 27). An untyped method, or an idea
    that maps from a step the solution does not name, cannot be represented as a
    grounded content plan.
    """


class ContentPlanTenantBoundaryError(CommercialError):
    """A content plan mixed assets or ideas that do not belong to one client.

    SPEC.md sections 3 and 9 make ``tenant_id`` on every tenant resource and
    query a hard invariant. A plan whose method, currency, themes or ideas span
    more than one client cannot be represented as one content plan.
    """


class ContentPlanThemeError(CommercialError):
    """A content plan's themes did not group around the one locked currency.

    The Extract motion groups the extracted ideas around the one primary
    currency (SPEC.md section 12.5; canon file 27), so each theme must advance a
    measure of that same locked currency. A theme that names a measure the
    currency does not carry cannot be represented as a currency-aligned theme.
    """


class ContentPlanObservationError(CommercialError):
    """A content plan was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The plan
    describes the content that will be planned, produced and published, while any
    measured reach is a separate observation, so a content plan is never an
    observation.
    """


class InvalidLeadMagnetKitError(CommercialError, ValueError):
    """A lead-magnet kit left a required canon field unstated.

    The canon's lead-magnet clinic (High Ticket Funnels 03) requires a named
    owner, the one hot step, a name, a promise, a timeline, the seven-element PDF
    package, the picture of the thing itself, a clear next action and the paired
    authority video. A blank identity or a missing PDF section cannot be
    represented as the kit the canon prescribes.
    """


class LeadMagnetKitDependencyError(CommercialError):
    """A lead-magnet kit depended on a method or step it cannot map from.

    The canon's first rule is that a lead magnet is never built from scratch: it
    is one hot step of the product roadmap (High Ticket Funnels 03, "the wheel of
    awesome"). An untyped Signature Solution or Primary Currency, or a hot step
    the solution does not name, cannot be represented as a grounded kit.
    """


class LeadMagnetKitTenantBoundaryError(CommercialError):
    """A lead-magnet kit mixed assets that do not belong to one client.

    SPEC.md sections 3 and 9 make ``tenant_id`` on every tenant resource and
    query a hard invariant. A kit whose method or currency spans more than one
    client cannot be represented as one kit.
    """


class LeadMagnetKitFormatError(CommercialError):
    """A lead-magnet kit broke the canon's format, delivery or time rules.

    The canon refuses an ebook, webinar, mini course, strategy session, quiz,
    guide or white paper; requires the name to imply the format; requires the
    two-step opt in; requires delivery by email rather than the thank-you page;
    and requires the magnet to fit in about ten minutes (High Ticket Funnels 03).
    A kit that breaks any of these cannot be represented as the prescribed kit.
    """


class LeadMagnetKitObservationError(CommercialError):
    """A lead-magnet kit was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The kit
    describes the magnet that will be built and delivered, while any measured
    opt-in rate or cost per lead is a separate observation, so a kit is never an
    observation.
    """
