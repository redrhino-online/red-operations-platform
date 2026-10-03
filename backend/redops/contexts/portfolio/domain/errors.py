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
