"""Named domain errors for the Portfolio bounded context (pure domain)."""

from __future__ import annotations


class PortfolioError(Exception):
    """Base class for portfolio domain rule violations."""


class InvalidUmbrellaPlanError(PortfolioError, ValueError):
    """An umbrella plan or one of its parts was built without required content.

    SPEC.md section 3 gives the Portfolio context the engagement roadmap, and
    SPEC.md section 12.5 records the canon's umbrella planning (the Online
    Business Launch Map and the one-page Bulletproof Business Plan, canon files
    00 and 01) as a canon gap. The canon puts the whole strategy on one page
    (canon file 00: "it puts this whole strategy into one really powerful page")
    and requires the business plan's goals and metrics to be specific and
    relevant (canon file 01). An umbrella plan names its owner, the client
    workspace it belongs to, the versioned stage template it plans over, the
    canon's launch-map sections, at least one specific measurable business target
    and at least one review. A blank identity, an empty section, target or review
    set, an untyped section, or a target without a metric, goal or due date
    cannot be represented as a plan.
    """


class UmbrellaPlanTenantBoundaryError(PortfolioError):
    """An umbrella plan mixed in an asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. An
    umbrella plan belongs to the tenant of the client workspace it plans, so a
    plan cannot cross a tenant boundary.
    """


class UmbrellaPlanDependencyError(PortfolioError):
    """An umbrella plan was not grounded on a workspace and a stage template.

    The canon's launch map is "the whole strategy ... into one really powerful
    page" (canon file 00) over the 12-week program, which SPEC.md section 4
    represents as the versioned stage 0 to 10 template. An umbrella plan must be
    grounded on a typed client workspace and a typed versioned stage template
    before it can be a plan over the whole pipeline, and every section must cover
    stages the template actually names.
    """


class UmbrellaPlanFormatError(PortfolioError):
    """An umbrella plan broke the canon's single-page planning shape.

    The canon's launch map has four parts -- the foundation, the signature
    solution, the funnel and the floodgates (canon file 00) -- and the bulletproof
    business plan is deliberately one page that forces clarity (canon file 01:
    "the whole thing behind this particular plan being one page ... forces you to
    be clear, concise, and on point"). The plan must carry each canon section
    once, cover every template stage exactly once, and keep each business target
    dated on or after the plan was created; otherwise the single-page engagement
    plan is incoherent or leaves part of the pipeline unplanned.
    """


class UmbrellaReviewCadenceError(PortfolioError, ValueError):
    """A review did not keep the canon's 90-day revisit cadence.

    The canon warns that a business plan that is treated as an exercise and put
    on the shelf loses its value and is not redone (canon file 01: "they treat it
    as an exercise and they put it on the shelf and they're not redoing it every
    90 days and keeping up with the weekly actions"). Each review must set its
    next revisit exactly one 90-day quarter after it was reviewed, so the plan
    carries its own revisit discipline rather than relying on memory.
    """


class UmbrellaReviewOrderError(PortfolioError):
    """A review was recorded out of order or before the plan existed.

    A review history is append-only in time, so a review cannot be dated before
    the plan was created or before the previous review's next revisit date;
    otherwise the revisit trail is not a real chronology (SPEC.md section 3,
    Decision invariant: decision history is append only).
    """


class UmbrellaPlanOverdueError(PortfolioError):
    """An umbrella plan was not revisited within its own 90-day cadence.

    The canon requires the plan to be revisited on a regular basis and redone
    every 90 days (canon file 01). An overdue plan cannot be presented as the
    live engagement plan, so the review policy refuses it until a fresh review
    records the revisit.
    """


class UmbrellaPlanObservationError(PortfolioError):
    """An umbrella plan was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. An umbrella
    plan is the engagement's intended strategy and targets, while any measured
    movement stays a separate observation, so a plan is never an observation.
    """


class InvalidOpportunityError(PortfolioError, ValueError):
    """A portfolio opportunity was built without required content.

    SPEC.md section 7 lists ``/opportunities`` and SPEC.md section 1 puts
    portfolio expansion in the product contract; the canon's Grow motion splits
    the foundation offer into smaller offers that are new entry points and raise
    customer lifetime value (canon files 11 and 12, mapped in SPEC.md section
    12.3). An opportunity names its tenant, a title, a typed kind, the exact
    approved asset version it derives from, its investment case, its expected
    outcome, a named owner and a next action (SPEC.md sections 3 and 4). A blank
    identity, an untyped kind, a versionless source or a missing owner, action or
    case cannot be represented as an opportunity.
    """


class OpportunityTenantBoundaryError(PortfolioError):
    """An opportunity mixed in a source asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. An
    opportunity belongs to the tenant of the client portfolio it expands, so it
    cannot be grounded on another tenant's asset.
    """


class OpportunityAuthorityError(PortfolioError):
    """An opportunity was represented as already invested in or launched.

    SPEC.md section 1 forbids representing a draft or model inference as client
    approved fact, and SPEC.md section 5 makes agent output a proposal that is
    never an implicit grant of authority. The canon's Grow offers are a future
    portfolio expansion (canon files 11 and 12). The register records only a
    proposal: an opportunity stays proposed until a human investment authority
    acts, so it cannot be stored or read back as approved, invested or launched.
    """


class OpportunityConflictError(PortfolioError):
    """A stored opportunity was re-stated with different content under its id.

    An opportunity register is append-only (SPEC.md section 3, Decision
    invariant: decision history is append only). A same-id re-statement with
    different content is refused rather than silently rewritten; a materially
    different opportunity is a new identity.
    """


class InvalidDeliveryLadderError(PortfolioError, ValueError):
    """A delivery ladder was built without required content.

    SPEC.md section 12.5 records the canon's delivery ladder and ascension as a
    canon gap (one-to-one beta, live cohort, evergreen; a 90-day roadmap audit;
    one deliverable per step), and the implementation plan's backlog item G5
    names a typed artifact that represents the client's own delivery (Serve) and
    the next-offer path. A ladder names its tenant, a named owner, the same-tenant
    stage 5 ``ProductProgram`` it delivers, the canon rungs, one deliverable per
    program step, at least one 90-day roadmap audit, at least one success goal and
    at least one ascension offer. A blank identity, an empty rung, step, audit,
    goal or offer set, or an untyped part cannot be represented as a delivery
    ladder.
    """


class DeliveryLadderTenantBoundaryError(PortfolioError):
    """A delivery ladder mixed in a program from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    delivery ladder belongs to the tenant of the client whose program it
    delivers, so it cannot be grounded on another tenant's program.
    """


class DeliveryLadderDependencyError(PortfolioError):
    """A delivery ladder was not grounded on a program or named an unknown step.

    The canon's delivery playbook delivers the productized program one module per
    week (synthesized ``ops/playbooks/delivery.md``), so a ladder must be grounded
    on a typed same-tenant stage 5 ``ProductProgram`` and every step deliverable
    and ascension offer must name a step the program actually has.
    """


class DeliveryLadderFormatError(PortfolioError):
    """A delivery ladder broke the canon's delivery shape.

    The canon's delivery ladder starts one to one, moves to a live cohort and
    then records an evergreen program (canon files 11 and 12; synthesized
    ``ops/playbooks/delivery.md``), and every module gives the client a working
    tool. The rungs must be an ordered, duplicate-free subsequence of the canon
    ladder beginning at one-to-one, the step deliverables must be exactly one per
    program step in program order, and each finished step carries at most one
    small offer; otherwise the ladder is not the canon's ascension path.
    """


class DeliveryAuditCadenceError(PortfolioError, ValueError):
    """A roadmap audit did not keep the canon's 90-day cadence.

    The canon's delivery playbook audits the client against their own roadmap
    once every 90 days and finds the missing step (synthesized
    ``ops/playbooks/delivery.md``). Each audit must set its next audit exactly one
    90-day quarter after it was performed, so the ladder carries its own audit
    discipline rather than relying on memory.
    """


class DeliveryAuditOrderError(PortfolioError):
    """A roadmap audit was recorded out of order or before the ladder existed.

    An audit history is append-only in time, so an audit cannot be dated before
    the ladder was created or before the previous audit's next audit date;
    otherwise the audit trail is not a real chronology (SPEC.md section 3,
    Decision invariant: decision history is append only).
    """


class DeliveryGateError(PortfolioError):
    """A delivery ladder was closed without meeting the goals set at kickoff.

    The canon's delivery playbook measures results against the goals set at
    kickoff and says to fix the plan before closing when the results do not match
    (synthesized ``ops/playbooks/delivery.md``). Closing therefore requires a
    caller-supplied result for every goal, and every result must be met; a missing
    or unmet goal, or a result for a goal the ladder does not carry, is refused.
    """


class DeliveryLadderObservationError(PortfolioError):
    """A delivery ladder was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. A delivery
    ladder is the client's intended delivery and ascension plan, while any
    attendance, completion or result stays a separate observation, so a ladder is
    never an observation.
    """


class InvalidPartnershipPlanError(PortfolioError, ValueError):
    """A partnership plan or one of its parts was built without required content.

    SPEC.md section 12.5 records the canon's partnership line and certification as
    a canon gap (the four-offer path, the partnership loop, renewal and win-back,
    the referral and partner plan, community rules, the reputation track and the
    certified consultant standard), and the implementation plan's backlog item G6
    names typed artifacts that keep every client with a next step. A plan names its
    tenant, a named owner, the same-tenant stage 5 ``ProductProgram`` it extends,
    the four-offer path, the partnership loop, a regular check-in, a referral plan,
    community rules, a reputation track and a certification standard. A blank
    identity, an empty offer, move, rule or skill set, or an untyped part cannot be
    represented as a partnership plan.
    """


class PartnershipTenantBoundaryError(PortfolioError):
    """A partnership plan mixed in a program from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    partnership plan belongs to the tenant of the client whose program it extends,
    so it cannot be grounded on another tenant's program.
    """


class PartnershipDependencyError(PortfolioError):
    """A partnership plan was not grounded on a program or named an unknown offer.

    The canon's partnership playbook extends the productized program into a
    four-offer path (synthesized ``ops/playbooks/partnership.md``), so a plan must
    be grounded on a typed same-tenant stage 5 ``ProductProgram`` and its referral
    plan must name the partner offer the plan actually carries.
    """


class PartnershipFormatError(PortfolioError):
    """A partnership plan broke the canon's partnership shape.

    The canon's four-offer path is a free entry, a small offer, a core offer and a
    partner offer, each leading to the next, and the partnership loop is retain,
    grow, refer and renew (canon files 11 and 12; synthesized
    ``ops/playbooks/partnership.md``). The offers and moves must each be the canon
    set in order without repeats, the community rules must be simple and unique,
    and the reputation track must cover reviews, stories and press; otherwise the
    plan is not the canon's partnership line.
    """


class PartnershipGateError(PortfolioError):
    """A partnership plan asked for referrals before a win.

    The canon's partnership playbook says to ask for referrals after a win, not
    before, and lists asking too early as a common failure (synthesized
    ``ops/playbooks/partnership.md``). A referral plan that does not ask after a
    win is refused, so the plan cannot represent a premature referral ask.
    """


class PartnershipObservationError(PortfolioError):
    """A partnership plan was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. A partnership
    plan is the client's intended retention and expansion path, while any renewal,
    referral or review stays a separate observation, so a plan is never an
    observation.
    """


class CertificationStandardError(PortfolioError, ValueError):
    """A certification standard was built without the canon's required content.

    The canon's certification playbook keeps the standard short -- "a few clear
    skills, not a long list" -- requires a clear exam pass mark and rechecks the
    standard every year (synthesized ``ops/playbooks/certification.md`` and
    ``ops/sops/certification-exam.md``). A standard must carry at least one and at
    most a short list of unique, non-blank skills, a non-blank pass mark and a
    yearly recheck; otherwise it cannot be represented as the certified consultant
    standard.
    """


class CertificationProofError(PortfolioError):
    """An operator was certified without a real result or a passed exam.

    The canon's proof rule is "certify only after a real result. No result, no
    badge", and each certified person must pass the exam (synthesized
    ``ops/playbooks/certification.md``). Certifying an operator who has no real
    result or who did not pass the exam is refused, so the register cannot claim a
    certification the canon does not allow.
    """
