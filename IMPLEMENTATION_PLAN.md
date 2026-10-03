# RED Operations Platform: Implementation Plan

Version: 0.2, September 27, 2026. Planning basis: the accompanying SPEC.md. This is a fork implementation plan, not a claim that the OpenExecutive repository or home cluster has been inspected.

## Current cycle status

- Cycle timestamp: 2026-10-03T05:56:20Z (Ralph cycle 119).
- Selected item: build the canon's enrollment and sales call (canon files 00, 06,
  13, 14, 21 and 24) as an explicit stage 8/9 asset over the same-tenant stage 8
  `FunnelIntegration`. SPEC.md section 12.5 records the enrollment and sales call --
  the pre-call homework qualifier, the medical-style frame/examine/prescribe/
  prognosis, the acceptance and rejection ("red velvet rope") criteria and live
  payment and checkout -- as a canon gap "between stages 8 and 10" whose intended
  use is to "convert an engaged prospect into a client with a defined,
  authority-preserving process", and permits it as "explicit stage 8/9 assets"
  rather than a new Sell/Enroll stage. It was the named highest priority ready next
  item after cycle 118. It outranks the remaining audience and retargeting delivery
  assets because enrollment sits on the critical path between stage 8 and stage 10
  and the asset route changes no gate contract, while those delivery assets are
  operations surface with a narrower pipeline effect.
- Outcome: completed and verified (single item; no second item started).
- Evidence: the canon enrollment and sales call now live in the Execution bounded
  context (`backend/redops/contexts/execution/domain/enrollment.py`) with
  `EnrollmentStep`, `EnrollmentStepKind`, `EnrollmentHomework`,
  `EnrollmentQualification`, `EnrollmentPayment`, `EnrollmentPaymentMethod` and
  `EnrollmentPlan`, the named errors `InvalidEnrollmentError`,
  `EnrollmentDependencyError`, `EnrollmentTenantBoundaryError` and
  `EnrollmentObservationError`, and `EnrollmentReadinessPolicy`. The plan binds a
  named owner and the accountable human closer to a same-tenant complete stage 8
  `FunnelIntegration`; requires exactly the canon's four explicitly named call
  stages (frame, examine, prescribe, prognosis; canon file 00) once each in order,
  each carrying the red-flag opt-out check the canon applies "every step of the
  way"; requires a pre-call homework that draws on "a piece of my signature
  solution" and schedules "within 72 hours. No more than that" (canon file 21);
  requires the "red velvet rope" of at least one accept and one reject criterion
  (canon file 06); and requires live payment over a typed method with a positive
  deposit because the canon says "always have the purse on the phone" and "accept
  their money live" (canon file 21). It refuses a blank identity, an untyped or
  cross-tenant funnel, a typed-component substitute, a
  missing/extra/duplicate/out-of-order call stage, a homework window outside the
  three-day bound, a one-sided rope, a non-positive deposit or a payment not
  captured live; `EnrollmentReadinessPolicy` refuses to run the call before the
  funnel has passed Funnel Complete; and it is never an observation. It is an
  explicit stage 8/9 asset, not a new required gate kind (a methodology-owner
  decision, SPEC.md section 12.5). New behavioral coverage: 19 tests in
  `tests/unit/execution/test_enrollment.py`. Running
  `PYTHONPATH=backend python3 -m unittest discover -s tests -p 'test_*.py'`
  reports 1392 passed, up from 1373. `python3 -m pyflakes backend/redops tests` is
  clean. `ruff` and `mypy` remain uninstalled.
- New findings: the canon explicitly names four enrollment call stages (frame,
  examine, prescribe, prognosis) but the enumerated "six step process" it promises
  is absent from the supplied files (SPEC.md section 12.6), so the artifact models
  only the four named stages and records the gap rather than inventing the missing
  two; the red velvet rope accept and reject criteria are stated in canon file 06,
  so its citation was added to the section 12.5 seed set. Grounding the call on a
  complete same-tenant funnel gives the stage 8 "sales handoff and SOPs" a real,
  owner-bound artifact without changing the stage 8 gate contract.
- Blockers: unchanged named-owner decisions -- where RED code lives (already de
  facto `backend/redops`), storage strategy given the SQLite reality, tenant model
  given slot-based single-active-client isolation, the lifecycle transition graph
  assumed in cycle 56, scheduler/worker topology, the client-designated approver
  identities, and pilot metric targets. Persistence and the Operations delivery
  adapter still depend on the storage ADR; the stage 9 compliance projection still
  needs a named-owner decision on a canonical kind.
- Highest priority ready next item: build the canon's content syndication and
  recycling schedule (canon files 29, 30 and 31) as a stage 6/10 planning asset
  over the same-tenant Commercial `ContentRoadmap`, so each content topic carries a
  typed per-channel syndication cadence, a dollar-a-day promotion budget and
  recycled derivative formats, binds a named owner and reports the topics it does
  not yet syndicate. SPEC.md section 12.5 lists the Content Blitz
  produce/publish/promote/syndicate cycle, the ten-second-view audience campaign
  and dollar-a-day promotion as the remaining part of the audience-building and
  content flywheel gap (canon files 25-31), and it is the largest canon-covered gap
  still unimplemented. It outranks the retargeting remainder (the invisible opt-in
  offer and the banner-ad spec and swipe file, canon 33 and 34), which are
  tactical asset libraries with a narrower pipeline effect, and the bounded wiring
  follow-ups (awareness map, matchmaker, funnel finder, transformations, umbrella
  and enrollment into their gates or views), which each need a methodology-owner
  decision on a required kind. Prerequisite: read canon files 29, 30 and 31 before
  shaping, ground the schedule on the same-tenant Commercial `ContentRoadmap`
  (Commercial already owns the roadmap, so no new cross-context import is needed),
  keep it a planning asset inside stages 6 and 10 rather than a required gate kind,
  and record that the content measurement loop it feeds remains a separate stage 10
  observation.
- Deferred cross-context items: the Operations delivery adapter plus durable
  notification log (blocked on the storage ADR); per-kind stage 9 through 10
  asset content schemas; a stage-parameterized gate recorder/handler refactor;
  projecting the compliance package onto a canonical stage 9 gate kind
  (methodology-owner decision); wiring the Swimlanes, umbrella, transformation,
  awareness/matcher/finder and enrollment plans into the production view, the
  command center or a required gate kind (methodology-owner decisions); and all
  persistence.
  [DONE 2026-10-03 (Ralph cycle 119): built the canon's enrollment and sales call
  as the pure Execution `EnrollmentPlan` (`EnrollmentStep`, `EnrollmentStepKind`,
  `EnrollmentHomework`, `EnrollmentQualification`, `EnrollmentPayment`,
  `EnrollmentPaymentMethod`), which binds a named owner and the accountable human
  closer to a same-tenant complete stage 8 `FunnelIntegration`, carries exactly the
  canon's four explicitly named call stages frame, examine, prescribe and prognosis
  once each in order, each with the red-flag opt-out check the canon applies every
  step of the way, requires a pre-call homework drawing on a piece of the signature
  solution and scheduling within the canon's three-day window, requires the red
  velvet rope of at least one accept and one reject criterion, requires live
  payment over a typed method with a positive deposit, refuses a blank identity, an
  untyped or cross-tenant funnel, a typed-component substitute, a
  missing/extra/duplicate/out-of-order stage, an out-of-window homework, a
  one-sided rope, a non-positive deposit or a deferred payment, and is never an
  observation, with `EnrollmentReadinessPolicy` refusing the call before the funnel
  has passed Funnel Complete (SPEC.md section 12.5; canon files 00, 06, 13, 14, 21
  and 24); verified by `tests/unit/execution/test_enrollment.py` (19 tests, full
  suite 1392 passed). SPEC.md section 12.6 leaves the enumerated six-step process
  and the dedicated sales/enrollment training absent from the supplied canon, so
  the shape is extracted from the covered files and recorded as a documented gap.]
  [DONE 2026-10-03 (Ralph cycle 118): built the canon's thirteen transformations
  as the pure Method `Transformation`, `TransformationScope` and
  `ThirteenTransformations` -- the set binds the Million Dollar Message and the
  same-tenant stage 4 `SignatureSolution` to exactly one overall shift (titled with
  the Million Dollar Message and moving between the solution's declared starting
  and final states), exactly three phase shifts and exactly nine step shifts
  (thirteen total), each matching the solution's own phase and step start and final
  states, and refuses a blank or no-op shift, a missing/extra/duplicate/non-typed
  shift, a shift naming a phase or step the solution does not have, a cross-tenant
  solution or shift and a set not grounded on a typed solution, and is never an
  observation (SPEC.md section 12.5; canon files 09 and 10); verified by
  `tests/unit/method/test_transformations.py` (31 tests, full suite 1373 passed),
  so the stage 4 method structure now carries the canon's explicit titled from/to
  transformations without changing the stage 4 gate contract.]
  [DONE 2026-10-03 (Ralph cycle 117): built the canon's Swimlanes channel model as
  the pure Execution `SwimlaneChannel`, `SwimlaneMove` and `SwimlanesPlan` -- the
  channel type is exactly the canon's five channels (messages, ads, human
  outreach, offline and direct mail, content; SPEC.md section 12.5), a move names
  the channel, the stalled step, the distinct next step, the vehicle and the one
  action it presents and refuses a move that keeps the prospect on the same step
  (canon file 13), and the plan binds a named owner and the same-tenant stage 8
  `FunnelIntegration` to at least one typed move, reports covered and missing
  channels and is never an observation; `SwimlaneCoveragePolicy.require_all_channels`
  refuses a plan that relies on too few channels (canon file 34: "you can't be
  single source dependent"; SPEC.md section 12.5; canon files 13, 14, 33 and 34);
  verified by `tests/unit/execution/test_swimlanes.py` (15 tests, full suite 1342
  passed), so the stalled-prospect recovery channel model is now a typed,
  tenant-scoped planning asset and the Swimlanes canon gap is complete. It lives
  in Execution because Commercial cannot import the Execution `FunnelIntegration`
  without a production-commercial-execution import cycle. Keeping it a planning
  asset rather than a stage 8/10 gate kind is a documented methodology-owner
  decision.]
  [DONE 2026-10-03 (Ralph cycle 116): built the canon's umbrella planning as the
  new pure Portfolio `UmbrellaPlan` (`LaunchMapSection`, `UmbrellaSection`,
  `BusinessTarget`, `QuarterlyReview`) -- the plan binds a named owner, a
  same-tenant `ClientWorkspace` and a versioned `StageTemplate` to exactly the
  canon's four launch-map sections (Foundation, Signature Solution, Funnel,
  Floodgates; canon file 00), covers every template stage exactly once, requires
  at least one specific measurable business target and a 90-day revisit history,
  and `UmbrellaReviewPolicy.require_current` refuses an overdue plan (SPEC.md
  section 12.5; canon files 00 and 01); verified by
  `tests/unit/portfolio/test_umbrella_plan.py` (27 tests, full suite 1327
  passed), so umbrella planning is now a typed, tenant-scoped plan over the whole
  pipeline and the gap is complete. Mapping the canon's four strategy parts onto
  stages 0-2/3-5/6-9/10 is a documented intentional deviation from the canon's
  12-week calendar.]
  [DONE 2026-10-03 (Ralph cycle 115): built the canon's Content Roadmap as the
  pure Commercial Design `ContentBeat`, `ContentChannel`, `ContentTopic`,
  `ContentRoadmap` and `ContentDistributionPolicy` -- a topic maps from a named
  step of a same-tenant stage 4 `SignatureSolution`, names the audience question
  it answers, at least one typed duplicate-free channel and exactly the Authority
  Amplifier beat order Promise, Proof, Problems, Steps, Context, Action; the
  roadmap binds a named owner, the same-tenant solution and at least one unique
  topic, reports the steps it covers and misses, and is never an observation;
  `ContentDistributionPolicy.require_minimum_reach` refuses a topic that does not
  reach the canon's minimum blog, YouTube and Facebook channels (SPEC.md section
  12.5; canon files 25-31); verified by
  `tests/unit/commercial/test_content_roadmap.py` (22 tests, full suite 1300
  passed), so the stage 6 content planning is now a typed, tenant-scoped asset
  and the audience-building and content flywheel gap is partially implemented.]
  [DONE 2026-10-03 (Ralph cycle 114): built the canon's Funnel Finder as the
  pure Commercial Design `FunnelProfile`, `FunnelType`, `OfferPriceBand` and
  `FunnelFinder` -- a profile carries the canon's four finder factors (technical
  level, experience, a typed offer price band and business model), the finder
  narrows at least two canon funnel types (liquid, local, CAC, webinar, quiz,
  launch) to exactly the one selected with a rationale, refuses a duplicate or
  unconsidered type and a cross-tenant profile, and
  `FunnelSelectionPolicy.require_price_fit` refuses a high-ticket offer with a
  self-serve funnel and a low-ticket offer with the sales-call CAC funnel
  (SPEC.md section 12.5; canon files 13 and 14); verified by
  `tests/unit/commercial/test_funnel_finder.py` (15 tests, full suite 1278
  passed), so the pre-stage-8 funnel selection is now a typed, tenant-scoped
  planning asset rather than prose and the positioning and decision tools canon
  gap is complete.]
  [DONE 2026-10-03 (Ralph cycle 113): built the canon's Target Market Matchmaker
  as the pure Commercial Design `TargetMarketCandidate` and
  `TargetMarketMatchmaker` -- a candidate carries the canon's five match criteria
  (passion, problem, profit, reachability, point-A-to-point-B pathway), the match
  narrows at least two candidates to exactly the one selected, grounds the chosen
  market on a same-tenant `MarketAwarenessMap`, refuses a duplicate candidate or a
  selected market that is not among the candidates, and
  `TargetMarketMatchPolicy.require_servable` refuses a match whose chosen market's
  awareness position is not initially targetable (SPEC.md section 12.5; canon file
  00); verified by `tests/unit/commercial/test_target_market_matchmaker.py` (12
  tests, full suite 1263 passed), so the target market decision is now a typed,
  tenant-scoped planning asset rather than prose. The Funnel Finder remains in
  this canon gap.]
  [DONE 2026-10-03 (Ralph cycle 112): built the canon's five market awareness
  levels as the pure Commercial Design `MarketAwarenessLevel` and
  `MarketAwarenessMap` -- the map types the stage 1 `awareness-map` canonical kind
  with a canon level (completely unaware, problem aware, solution aware, product
  aware, most aware), requires research evidence and message requirements, refuses
  a retarget level that is not strictly more aware than the primary level, projects
  onto the `awareness-map` kind as exact `StageAssetVersion` evidence, and
  `MarketAwarenessPolicy.require_targetable` refuses a map whose primary level is
  the completely unaware (SPEC.md section 12.3 stage 1 and section 12.5; canon file
  04); verified by `tests/unit/commercial/test_market_awareness.py` (12 tests, full
  suite 1251 passed), so the awareness position is now a typed, versionable gate
  asset rather than a free string. The Target Market Matchmaker and Funnel Finder
  remain in this canon gap.]
  [DONE 2026-10-03 (Ralph cycle 111): built the canon's follow-up and nurture
  lifecycle as the pure Commercial Design `NurtureAudienceState`, `NurtureModality`,
  `NurtureMessage`, `NurtureSequence` and `NurturePlan` -- the plan grounds every
  message on a named step of a same-tenant stage 4 `SignatureSolution`, names the
  prospect state it recovers, uses the 5P modality (where ping is the one-question
  survey), re-engages non-openers with distinct headlines, binds the sequences to a
  named owner, reports the canon states it does not yet cover and is never an
  observation -- so the follow-up and nurture canon gap is implemented for its
  post-stage-10 planning scope (SPEC.md section 12.3 and section 12.5; canon files
  15, 24, 33, 34); verified by `tests/unit/commercial/test_nurture_lifecycle.py`
  (32 tests, full suite 1239 passed). The dedicated email/follow-up module is
  absent from the supplied canon (SPEC.md section 12.6), so this is a documented
  gap, not canon-complete.]
  [DONE 2026-10-03 (Ralph cycle 110): built the canon's retargeting roadmap as the
  pure Measurement `TrackingCode`, `ConversionGoal`, `RetargetingAudience`,
  `RetargetingCampaign`, `RetargetingChannel`, `RetargetingStep` and
  `RetargetingPlan` -- the plan binds a tracking code, conversion goals,
  retargeting lists and focused campaigns to a named owner and one tenant, requires
  the tracking code and goal prerequisite before a list or campaign, refuses a
  campaign that targets no new named funnel step or an undeclared list, and is
  never an observation -- so the retargeting-system canon gap is implemented for
  its stages 8 and 10 planning scope (SPEC.md section 4 stage 8 and section 12.3;
  canon files 33 and 34); verified by `tests/unit/measurement/test_retargeting.py`
  (35 tests, full suite 1207 passed).]
  [DONE 2026-10-03 (Ralph cycle 109): built the canon's split-test logging as the
  pure Measurement `SplitTestMode`, `SplitTestChange` and `SplitTest` -- the log
  binds to the same-tenant owner-approved `ImprovementProposal`, changes exactly
  one variable (which must be the optimization's own lever), records the
  pause-and-clone or run-concurrent mode over a closed test window, and refuses a
  no-op change, an unapproved optimization, a cross-tenant optimization and a
  result read before its window closed, while never being an observation -- so the
  advertising and forecast dashboard canon gap is fully implemented (SPEC.md
  section 4 stage 10 and Phase 5; canon files 22, 23 and 24); verified by
  `tests/unit/measurement/test_split_test.py` (15 tests, full suite 1172 passed).]
  [DONE 2026-10-03 (Ralph cycle 108): built the canon's advertising scaling rule
  as the pure Measurement `LearningPhase`, `ScalingAction`, `ScalingRecommendation`
  and `AdScalingPolicy` -- the policy holds while the campaign learns, bids up the
  funnel below the caller's leads-per-day floor, scales up at or below the target
  cost per lead from `FunnelEconomics.target_cost_per_lead` and pauses and revisits
  above it, refusing a placeholder figure, a wrong-shaped metric, a cross-tenant
  observation and a non-positive target return, and the recommendation always
  needs a named owner's approval and can never be an observation -- so the
  advertising and forecast dashboard's remaining scope is split-test logging
  (SPEC.md section 4 stage 10 and Phase 5; canon files 22, 23 and 24); verified by
  `tests/unit/measurement/test_ad_scaling.py` (20 tests, full suite 1157 passed).]
  [DONE 2026-10-03 (Ralph cycle 107): built the canon's stage 10 funnel forecast
  equation as the pure Measurement `FunnelMetricRole`, `FunnelFigure`,
  `FunnelEconomics`, `FunnelForecast` value objects and the registry-grounded
  `funnel_figure` helper -- a figure carries its registered metric and explicit
  observed-or-placeholder basis, the economics computes the canon value chain and
  `target_cost_per_lead(target_return_on_ad_spend=...)`, and the forecast computes
  leads, booked/shown sessions, customers, revenue and return on ad spend from a
  scenario spend while refusing to be recorded as an observation, so the Metrics
  Matrix unit economics exist before real data and placeholder inputs stay
  planned-not-observed (SPEC.md section 4 stage 10 and Phase 5; canon files 22 and
  23); verified by `tests/unit/measurement/test_funnel_economics.py` (25 tests,
  full suite 1137 passed), so the advertising and forecast dashboard's remaining
  scope is the bid-up/bid-down scaling rule and split-test logging.]
  [DONE 2026-10-03 (Ralph cycle 106): populated the Governance production-manager
  view's `METRICS` reporting dimension -- `EngagementProductionView` now carries
  caller-supplied typed `MetricReportingView` rows (with `MetricMovement` and
  `MetricReportingBasis`, and the named `MetricReportingError` /
  `MetricReportingTenantBoundaryError`) and returns them from
  `dimension(ReportingDimension.METRICS)`, while the Measurement
  `metric_reporting_views` projection fills them from the newest same-tenant
  observed `MeasurementRecord` per registered `MetricDefinition` and attaches the
  measured before-and-after of the newest measured `ImprovementProposal`, so all
  eight spec-named reporting dimensions are now sourced and a production manager
  can see typed stage 10 metrics and their observed movement next to the gates
  (SPEC.md section 4 "separate eight reporting dimensions"; Phase 5; canon files
  22, 23 and 24); verified by `MetricReportingDimensionTests` in
  `tests/unit/governance/test_production_view.py` and
  `tests/unit/measurement/test_metric_reporting.py` (full suite 1112 passed), so a
  placeholder figure or another client's metric never appears as verified
  progress.]
  [DONE 2026-10-03 (Ralph cycle 105): floored the stage 10 improvement's "before"
  observation window at the owner approval date --
  `ImprovementMeasurementPolicy.require` now refuses an outcome whose before
  window ends after `ImprovementApproval.approved_on` with the named
  `ImprovementBeforeWindowError`, so the pre-change measurement is genuinely
  observed before the material change rather than merely before the after window,
  closing the last temporal edge in the stage 10 improvement chain (SPEC.md
  section 4 stage 10 and "performance recommendations require evidence and owner
  approval before material changes"; canon files 23 and 24: "you need a baseline
  of metrics" before optimizing); verified by the new
  `ImprovementBeforeWindowPrecedenceTests` in
  `tests/unit/measurement/test_improvement_loop.py` (full suite 1100 passed), so
  the improvement movement is now before-then-approved-then-after in time on
  both sides.]
  [DONE 2026-10-03 (Ralph cycle 104): floored the stage 10 improvement approval
  date at the establishment date of the baseline it optimizes --
  `ImprovementApprovalPolicy.require` now refuses an `ImprovementApproval` dated
  before `PerformanceBaseline.established_on` with the named
  `ImprovementApprovalPrecedenceError`, so a stage 10 optimization cannot be
  authorized before the baseline of metrics it changes existed (SPEC.md section 4
  stage 10 and "performance recommendations require evidence and owner approval
  before material changes"; canon files 23 and 24: "you need a baseline of
  metrics" before optimizing); verified by the new
  `ImprovementBaselineApprovalPrecedenceTests` in
  `tests/unit/measurement/test_improvement_loop.py` (full suite 1097 passed), so
  the stage 10 improvement chain is now baseline-then-approved-then-observed.]
  [DONE 2026-10-03 (Ralph cycle 103): floored the stage 10 baseline establishment
  date at the latest observed milestone -- `PerformanceBaselinePolicy.require` now
  refuses a `PerformanceBaseline` established before any milestone it records as
  observed with the named `PerformanceBaselinePrecedenceError`, so a baseline
  cannot report a lead, appointment or sale observed after its own establishment
  date, closing the last same-gate temporal edge at stage 10 (SPEC.md section 4
  stage 10 "Performance Baseline Established"; canon files 23 and 24: a baseline
  of metrics accumulates only after the campaign runs); verified by the new
  `BaselinePrecedenceTests` later-milestone cases in
  `tests/unit/execution/test_performance_baseline.py`, so every observed stage 10
  milestone is now both authorized-then-observed and establishment-ordered.]
  [DONE 2026-10-03 (Ralph cycle 102): required every observed stage 10 milestone
  to be observed no earlier than the stage 9 traffic authorization --
  `PerformanceBaselinePolicy.require` now refuses a `PerformanceBaseline` whose
  any observed `MilestoneObservation.observed_on` precedes the pinned
  `TrafficAuthorization.authorized_on`, with the new named
  `MilestoneObservationPrecedenceError`, so a baseline cannot report first
  qualified traffic -- or a later lead, appointment or sale -- observed before
  the authority that permitted traffic existed (SPEC.md section 4 stage 10
  "Performance Baseline Established"; canon files 23 and 24: a baseline of
  metrics accumulates only after the campaign runs); verified by the new
  `MilestoneAuthorizationPrecedenceTests` in
  `tests/unit/execution/test_performance_baseline.py` (31 tests, full suite 1092
  passed), so every observed stage 10 milestone is now authorized-then-observed,
  not merely establishment-ordered.]
  [DONE 2026-10-03 (Ralph cycle 101): required a stage 10 `PerformanceBaseline`
  to be established only once its own evidence exists --
  `PerformanceBaselinePolicy.require` now refuses an establishment date that
  precedes the later of the pinned stage 9 `TrafficAuthorization.authorized_on`
  and the observed first-qualified-traffic `MilestoneObservation.observed_on` with
  the new named `PerformanceBaselinePrecedenceError`, so a baseline cannot claim
  establishment before the traffic it reports was authorized and observed (SPEC.md
  section 4 stage 10 "Performance Baseline Established"; canon files 23 and 24: a
  baseline of metrics accumulates only after the campaign runs); verified by the
  new `BaselinePrecedenceTests` in
  `tests/unit/execution/test_performance_baseline.py` (28 tests, full suite 1089
  passed), so stage 10 now carries the same temporal discipline as the metric
  registry closed in cycle 100.]
  [DONE 2026-10-03 (Ralph cycle 100): required a `MeasurementRecord` to be
  written only once the window it covers has closed --
  `MeasurementRecord.__post_init__` now refuses a record whose `recorded_on` date
  falls before its `window.end` with the new named `MeasurementWindowOpenError`,
  so a still-open observation cannot enter the metric registry or ground any
  baseline or movement (SPEC.md section 3 Measurement aggregate and
  `MeasurementWindow`; Phase 5 "metric registry, event instrumentation,
  observations and experiment records"; canon files 23 and 24: wait before
  reading how the change did); verified by the new `MeasurementRecordTests`
  closure tests in `tests/unit/measurement/test_metric_registry.py` and the
  fixture-audit updates in `tests/unit/measurement/test_improvement_loop.py`
  (full suite 1086 passed), so the registry itself now carries the temporal
  discipline the improvement loop previously enforced only at the outcome.]
  [DONE 2026-10-03 (Ralph cycle 99): required a stage 10 improvement outcome's
  after observation window to have closed by its `measured_on` date --
  `ImprovementOutcome.__post_init__` now refuses an outcome measured before its
  after window ends with the new named `ImprovementResultWindowOpenError`, so an
  optimization cannot report a movement over a result period that has not yet
  elapsed (SPEC.md section 3 Measurement aggregate; section 4 stage 10; canon
  files 23 and 24: wait before reading how the change did); verified by the new
  `ImprovementOutcomeSettlementTests` in
  `tests/unit/measurement/test_improvement_loop.py` (46 tests, full suite 1083
  passed), so the stage 10 movement chain now requires the result window to have
  closed before the result is read.]
  [DONE 2026-10-03 (Ralph cycle 98): required the stage 10 improvement's after
  observation window to open no earlier than its named owner's approval date --
  `ImprovementMeasurementPolicy` now refuses an outcome whose after window starts
  before the pinned `ImprovementApproval.approved_on` with the new named
  `ImprovementObservationWindowError`, so an optimization cannot read a result
  over a period that predates the authorization of the change it measures (SPEC.md
  section 4: owner approval before material changes; section 4 stage 10; canon
  files 23 and 24: wait before reading how the change did); verified by the new
  `ImprovementApprovalPrecedenceTests` in
  `tests/unit/measurement/test_improvement_loop.py` (43 tests, full suite 1080
  passed), so the stage 10 movement chain is now approved-then-observed in time
  rather than only window-ordered.]
  [DONE 2026-10-03 (Ralph cycle 97): ordered the stage 10 improvement outcome's
  observation windows -- `ImprovementOutcome.__post_init__` now refuses an
  outcome whose before window ends on or after its after window starts with the
  named `ImprovementObservationError`, so an overlapping or reversed before/after
  cannot represent a measured movement (SPEC.md section 3 Measurement aggregate
  and `MeasurementWindow`; section 4 stage 10; canon files 23 and 24: wait before
  reading how the change did); verified by the new
  `ImprovementOutcomeTests` temporal tests and the updated `improvement_outcome`
  fixture in `tests/unit/measurement/test_improvement_loop.py` (40 tests, full
  suite 1077 passed), so a stage 10 optimization must read its after-state only
  after its before-state window has closed.]
  [DONE 2026-10-03 (Ralph cycle 96): grounded the stage 10 improvement outcome
  on typed observed measurements -- `ImprovementOutcome.before` and `.after` are
  now `MeasurementRecord`s attached to the outcome's registered `MetricDefinition`,
  a placeholder record or an identical before/after is refused with the new named
  `ImprovementObservationError`, `ImprovementOutcome.observations(baseline_id)`
  projects them onto baseline-citing `PerformanceClaim`s of kind OBSERVATION, and
  `ImprovementMeasurementPolicy` grounds the outcome on the approved
  `PerformanceBaseline` and checks the records directly (observed basis, same
  metric identity and version, same tenant) (SPEC.md section 3; canon files 23 and
  24); verified by `tests/unit/measurement/test_improvement_loop.py` (37 tests),
  so a stage 10 movement cites a window, basis, sample and source per side.]
  [DONE 2026-10-03 (Ralph cycle 95): grounded the stage 10 improvement loop on
  the cycle 93 metric registry -- `ImprovementProposal.metric` and
  `ImprovementOutcome.metric` are required same-tenant `MetricDefinition`s, the
  proposal and outcome subjects must equal the registered metric name, and
  `ImprovementMeasurementPolicy` refuses an outcome that measures a different
  metric identity or version with `ImprovementMetricError`,
  `ImprovementMetricBoundaryError` and `ImprovementMetricMismatchError` (SPEC.md
  section 3; canon files 23 and 24); verified by the `ImprovementMetricGroundingTests`
  in `tests/unit/measurement/test_improvement_loop.py` (10 tests), so a stage 10
  optimization can no longer be proposed or measured against a free-text metric.]
  [DONE 2026-10-03 (Ralph cycle 93): built the Measurement metric registry
  (`MetricDefinition`, `MetricUnit`, `MetricDirection`, `MetricFunnelStep`,
  `MeasurementWindow`, `MeasurementBasis`, `MeasurementRecord`,
  `MetricBaselinePolicy`) so a stage 10 observation pins a typed, versioned,
  tenant-scoped metric over an explicit window with a placeholder-or-observed
  basis, value, source and sample, a placeholder figure cannot establish a
  baseline, and an observed sample below the caller's minimum is refused (SPEC.md
  sections 3 and 4; Phase 5 "metric registry"; canon files 23 and 24 inform the
  funnel-step, unit, direction, basis and sample shape), verified by
  `tests/unit/measurement/test_metric_registry.py` (24 tests), so the `METRICS`
  reporting dimension and the improvement loop can now source a typed metric.]
  [DONE 2026-10-03 (Ralph cycle 92): built the Measurement improvement loop
  (`ImprovementProposal`, `ImprovementApproval`, `ImprovementOutcome`,
  `ImprovementState`, `ImprovementApprovalPolicy` and
  `ImprovementMeasurementPolicy`) in a new Measurement bounded context so a stage
  10 optimization stays a proposal until its named owner approves it, then records
  a measured before-and-after as two observations grounded on the same established
  same-tenant baseline, keeping the movement distinct from a causal conclusion
  (SPEC.md section 4, "performance recommendations require evidence and owner
  approval before material changes"; Phase 5, "one improvement is approved and
  measured"; canon files 23 and 24 inform the baseline-before-optimization and
  one-variable-at-a-time discipline); verified by
  `tests/unit/measurement/test_improvement_loop.py` (26 tests), so the stage 10
  optimization loop now exists as pure domain code and the engagement can stay in
  Optimization after launch rather than ending at activation.]
  [DONE 2026-10-03 (Ralph cycle 91): built the Operations notification delivery
  policy (`QuietHours`, `Notification`, `NotificationState`,
  `NotificationDeliveryPolicy`, `delivered_intervention_keys`) that delivers each
  open intervention card to its owner once, suppresses a delivery inside the
  owner's quiet hours as a recorded suppression, and deduplicates across query
  evaluations with a caller-supplied delivered-key set (SPEC.md section 7,
  "Notifications are deduplicated and respect owner and quiet hours"); verified by
  `tests/unit/operations/test_notification_policy.py` (22 tests), so the command
  center can now route owned, deduplicated, quiet-hour-respecting notifications
  without inventing an operator schedule.]
  [DONE 2026-10-03 (Ralph cycle 90): built the Operations command center
  intervention query and ranking (`Intervention`, `InterventionReason`,
  `InterventionSeverity`, `InterventionState`, `JourneyFailure`, `Commitment`,
  `InterventionRankingPolicy`) deriving per client the blocked critical path,
  overdue approvals, failed live journeys and nearing commitments from the
  Governance production view plus caller-supplied signals, with client, severity,
  reason, evidence, owner, next action, due time, state and affected builds,
  explainable surfacing, dismissal with rationale and deduplication (SPEC.md
  section 7, "Command center intervention fields"); verified by
  `tests/unit/operations/test_intervention_ranking.py` (18 tests), so the command
  center can now rank owned interventions over the full stage 0-10 pipeline.]
  [DONE 2026-10-03 (Ralph cycle 89): built the pure Governance
  production-manager view read model (`StageProductionView`,
  `EngagementProductionView`, `ReportingDimension`,
  `PRODUCTION_REPORTING_DIMENSIONS`) derived from the versioned `StageTemplate`
  and the durable `GateLedger` (SPEC.md section 4, "Gate record and production
  manager view"), answering per stage what should exist, what is present and
  approved, what is missing, who is accountable, which dependency blocks work,
  what approval is next and when it is due, separating the eight reporting
  dimensions and counting activity apart from gate completion; verified by
  `tests/unit/governance/test_production_view.py` (17 tests), so the full stage
  0-10 pipeline is now both writable and readable as verified progress and gate
  evidence.]
  [DONE 2026-10-03 (Ralph cycle 88): wired the stage 10 "Performance Baseline
  Established" `GateDecision` end to end with `StageTenGateAssembler`,
  `StageTenGateRecorder`, `RecordStageTenGateCommand` and
  `RecordStageTenGateHandler`, plus named errors `NotStageTenGateError` and
  `StageRunNotStageTenError` (canon-informed, SPEC.md section 12.3 stage 10 files
  22, 23, 29-31, 33, 34), binding the reviewed `PerformanceBaselinePackage` to the
  workspace tenant and authority registry, issuing one exact-version approval per
  canonical kind and closing the stage 10 `StageRun`; verified by
  `tests/unit/engagement/test_record_stage_ten_gate.py` (22 tests), so stage 10
  can now close and the full stage 0-10 pipeline is writable and its verified
  progress derivable.]
  [DONE 2026-10-03 (Ralph cycle 87): built the Execution
  `PerformanceBaselinePackage` bridge (canon-informed, SPEC.md section 12.3 stage
  10 files 22, 23, 29-31, 33, 34), projecting the reviewed stage 10
  `PerformanceBaseline` onto the twelve canonical stage 10 kinds as exact
  `StageAssetVersion` evidence with a `CANONICAL_BASELINE_KINDS` tuple and
  refusing a baseline that has not passed Performance Baseline Established;
  verified by `tests/unit/execution/test_performance_baseline_package.py` (12
  tests), so the stage 10 gate is now assembleable.]
  [DONE 2026-10-03 (Ralph cycle 86): wired the stage 9 "Launch Approved"
  `GateDecision` end to end with `StageNineGateAssembler`,
  `StageNineGateRecorder`, `RecordStageNineGateCommand` and
  `RecordStageNineGateHandler`, plus named errors `NotStageNineGateError` and
  `StageRunNotStageNineError` (canon-informed, SPEC.md section 12.3 stage 9 files
  01, 08, 21, 22, 24), binding the reviewed `LaunchQAPackage` to the workspace
  tenant and authority registry, issuing one exact-version approval per canonical
  kind and closing the stage 9 `StageRun`; verified by
  `tests/unit/engagement/test_record_stage_nine_gate.py` (22 tests), so stage 9
  can now close and stage 10 is unblocked pending its reviewed-asset bridge.]
  [DONE 2026-10-03 (Ralph cycle 85): built the Execution `LaunchQAPackage`
  bridge (canon-informed, SPEC.md section 12.3 stage 9 files 01, 08, 21, 22, 24),
  projecting the reviewed stage 9 `LaunchQA` onto the sixteen canonical stage 9
  kinds as exact `StageAssetVersion` evidence with a `CANONICAL_LAUNCH_KIND_CHECKS`
  map and refusing a QA that has not passed Launch Approved; verified by
  `tests/unit/execution/test_launch_qa_package.py` (13 tests), so the stage 9 gate
  is now assembleable.]
  [DONE 2026-10-03 (Ralph cycle 84): wired the stage 8 "Funnel Complete"
  `GateDecision` end to end with `StageEightGateAssembler`,
  `StageEightGateRecorder`, `RecordStageEightGateCommand` and
  `RecordStageEightGateHandler`, plus named errors `NotStageEightGateError` and
  `StageRunNotStageEightError` (canon-informed, SPEC.md section 12.3 stage 8
  files 13, 14, 21, 22), binding the reviewed `FunnelIntegrationPackage` to the
  workspace tenant and authority registry, issuing one exact-version approval per
  canonical kind and closing the stage 8 `StageRun`; verified by
  `tests/unit/engagement/test_record_stage_eight_gate.py` (22 tests), so stage 8
  can now close and stage 9 is unblocked pending its reviewed-asset bridge.]
  [DONE 2026-10-03 (Ralph cycle 82): wired the stage 7 "Authority Amplifier
  Approved" `GateDecision` end to end with `StageSevenGateAssembler`,
  `StageSevenGateRecorder`, `RecordStageSevenGateCommand` and
  `RecordStageSevenGateHandler`, plus named errors `NotStageSevenGateError`,
  `StageRunNotStageSevenError` and `AuthorityAmplifierNotApprovedError`
  (canon-informed, SPEC.md section 12.3 stage 7 files 13-18, 28), refusing an
  amplifier without final creative acceptance so the two-approval stage 7
  checkpoint cannot be bypassed; verified by
  `tests/unit/engagement/test_record_stage_seven_gate.py` (24 tests), so stage 7
  can now close and stage 8 is unblocked pending its reviewed-asset bridge.]
  [DONE 2026-10-03 (Ralph cycle 81): built the Production
  `AuthorityAmplifierPackage` bridge (canon-informed, SPEC.md section 12.3 stage 7
  files 13-18, 28), projecting the reviewed stage 7 `AuthorityAmplifier` onto the
  nine canonical stage 7 kinds as exact `StageAssetVersion` evidence and refusing
  an amplifier without its visual package; verified by
  `tests/unit/production/test_authority_amplifier_package.py` (12 tests), so the
  stage 7 gate is now assembleable.]
  [DONE 2026-10-03 (Ralph cycle 80): wired the stage 6 "Campaign Message
  Approved" `GateDecision` end to end with `StageSixGateAssembler`,
  `StageSixGateRecorder`, `RecordStageSixGateCommand` and
  `RecordStageSixGateHandler`, plus named errors `NotStageSixGateError`,
  `StageRunNotStageSixError` and `CampaignMessageNotApprovedError` (canon-informed,
  SPEC.md section 12.3 stage 6 files 06, 15, 24, 25-28), refusing an unapproved
  message so the congruence checkpoint cannot be bypassed; verified by
  `tests/unit/engagement/test_record_stage_six_gate.py` (24 tests), so stage 6 can
  now close and stage 7 is unblocked pending its reviewed-asset bridge.]
  [DONE 2026-10-03 (Ralph cycle 78): wired the stage 5 "Offer Locked"
  `GateDecision` end to end with `StageFiveGateAssembler`, `StageFiveGateRecorder`,
  `RecordStageFiveGateCommand` and `RecordStageFiveGateHandler`, plus named errors
  `NotStageFiveGateError` and `StageRunNotStageFiveError` (canon-informed, SPEC.md
  section 12.3 stage 5 files 11, 12); verified by
  `tests/unit/engagement/test_record_stage_five_gate.py` (22 tests), so stage 5
  can now close and stage 6 is unblocked pending its reviewed-asset bridge.]
  [DONE 2026-10-03 (Ralph cycle 77): built the Commercial `OfferPackage` bridge
  (canon-informed, SPEC.md section 12.3 stage 5 files 11, 12), projecting the
  reviewed stage 5 `DeliverySpecification` onto the twelve canonical stage 5
  kinds as exact `StageAssetVersion` evidence; verified by
  `tests/unit/commercial/test_offer_package.py` (10 tests), so the stage 5 gate
  is now assembleable.]
  [DONE 2026-10-03 (Ralph cycle 76): wired the stage 4 "IP Architecture Locked"
  `GateDecision` end to end with `StageFourGateAssembler`, `StageFourGateRecorder`,
  `RecordStageFourGateCommand` and `RecordStageFourGateHandler`, plus named errors
  `NotStageFourGateError` and `StageRunNotStageFourError` (canon-informed, SPEC.md
  section 12.3 stage 4 files 09, 10); verified by
  `tests/unit/engagement/test_record_stage_four_gate.py` (22 tests), so stage 4
  can now close and stage 5 is unblocked pending its reviewed-asset bridge.]
  [DONE 2026-10-03 (Ralph cycle 75): built the Commercial `SignaturePackage`
  bridge (canon-informed, SPEC.md section 12.3 stage 4 files 09, 10), projecting
  the reviewed Method `SignatureSolution` onto the twelve canonical stage 4 kinds
  as exact `StageAssetVersion` evidence; verified by
  `tests/unit/commercial/test_signature_package.py` (10 tests), so the stage 4
  gate is now assembleable.] [DONE 2026-10-03 (Ralph cycle 74):
  wired the stage 3 "Diagnostic Model Approved" `GateDecision` end to end with
  `StageThreeGateAssembler`, `StageThreeGateRecorder`, `RecordStageThreeGateCommand`
  and `RecordStageThreeGateHandler`, plus named errors `NotStageThreeGateError` and
  `StageRunNotStageThreeError` (canon-informed, SPEC.md section 12.3 stage 3 files
  07, 08); verified by `tests/unit/engagement/test_record_stage_three_gate.py`
  (22 tests), so stage 3 can now close and stage 4 is unblocked pending its
  reviewed-asset bridge.]
  [DONE 2026-10-03 (Ralph cycle 73): built the Commercial
  `DiagnosticPackage` bridge (canon-informed, SPEC.md section 12.3 stage 3 files
  07, 08) completing the Method `DiagnosticModel` with required `visual` and
  `explanatory_copy` and projecting it onto the ten canonical stage 3 kinds as
  exact `StageAssetVersion` evidence; verified by
  `tests/unit/commercial/test_diagnostic_package.py` (10 tests) plus two
  `DiagnosticModel` field tests, so the stage 3 gate is now assembleable.]
  [DONE 2026-10-03
  (Ralph cycle 72): wired the stage 2 "Currency Locked" `GateDecision` end to end
  with `StageTwoGateAssembler`, `StageTwoGateRecorder`, `RecordStageTwoGateCommand`
  and `RecordStageTwoGateHandler`, plus named errors `NotStageTwoGateError` and
  `StageRunNotStageTwoError` (canon-informed, SPEC.md section 12.3 stage 2 files
  04, 05, 06); verified by
  `tests/unit/engagement/test_record_stage_two_gate.py` (22 tests), so stage 2
  can now close and stage 3 is unblocked.]
  [DONE 2026-10-03
  (Ralph cycle 71): built the Commercial `CurrencyInventory`,
  `PositioningDecision`, `MillionDollarMessage` and `CurrencyPackage` bridge
  (canon-informed, SPEC.md section 12.3 stage 2 files 04, 05, 06) projecting the
  reviewed stage 2 assets onto the ten canonical kinds as exact
  `StageAssetVersion` evidence; verified by
  `tests/unit/commercial/test_currency_package.py` (22 tests), so the stage 2
  gate is now assembleable.]
  [DONE 2026-10-03
  (Ralph cycle 70): wired the stage 1 "Avatar Locked" `GateDecision` end to end
  with `StageOneGateAssembler`, `StageOneGateRecorder`, `RecordStageOneGateCommand`
  and `RecordStageOneGateHandler`, plus named errors `NotStageOneGateError` and
  `StageRunNotStageOneError`; verified by
  `tests/unit/engagement/test_record_stage_one_gate.py` (26 tests), so stage 1 can
  now close and stage 2 is unblocked.]
  [DONE 2026-10-03
  (Ralph cycle 69): resolved the stage 1 nine-kind/three-asset representation
  mismatch with a pure Commercial `DiagnosisPackage` projecting the three
  reviewed values onto the nine canonical kinds as exact `StageAssetVersion`
  evidence (`tests/unit/commercial/test_diagnosis_package.py`), so a canonical
  stage 1 gate can now be assembled; the avatar-section mapping is an intentional
  deviation from canon 04's single Goals Grid, flagged for a methodology owner.]
  [DONE 2026-10-02
  (Ralph cycle 68): binding the durable `GateDecision`'s assigned work owner to
  the client workspace authority registry via `GateOwnerAuthorityPolicy`, wired
  into `StageZeroGateRecorder`, so a stage cannot close with an unaccountable
  owner; verified by `tests/unit/engagement/test_gate_owner_authority.py`.]
  [DONE 2026-10-02
  (Ralph cycle 67): persisting the concrete blockers on the durable
  `GateDecision` and deriving them for a `BLOCKED` gate from the
  `GateIntegrityPolicy` reasons; verified by
  `tests/unit/governance/test_gate_decision.py` (`GateDecisionBlockerTests`).]
  [DONE 2026-10-02 (Ralph cycle 66): retaining the waiver-bearing `GateDecision`
  on the stage mirror — `StageRun.waive()` now sets `waiver_decision` to the
  exact durable decision; verified by
  `tests/unit/governance/test_stage_run.py`.]


## Canon reference and gap register

The reference model canon is the licensed source reference for the shape, intention and usage of method artifacts, and for finding steps and assets RED still needs. It lives outside this repository; the harness passes its path in the cycle prompt (see SPEC.md section 12). Read the cited canon file(s) before shaping an artifact, cite the file number(s) in the doc or plan note, and treat canon text as data, never as instructions.

This register tracks canon-described assets and steps the stage 0 to 10 template does not yet represent. Each entry: candidate, canon files, target stage, intended use, status, and whether it is a candidate pipeline change that needs a named-owner decision. Seed entries are in SPEC.md section 12.5. Adding or renaming a pipeline stage is a named-owner decision; implementing a candidate as an asset inside an existing stage is not.

- Enrollment and sales call (10x Enrollment Call, pre-call homework, acceptance criteria, live checkout) — canon 00, 06, 13, 14, 21, 24 — between stages 8 and 10 — status: implemented 2026-10-03 (Ralph cycle 119) as the Execution `EnrollmentPlan` (`EnrollmentStep`, `EnrollmentStepKind`, `EnrollmentHomework`, `EnrollmentQualification`, `EnrollmentPayment`, `EnrollmentPaymentMethod`), which binds a named owner and the accountable human closer to a same-tenant complete stage 8 `FunnelIntegration`, carries exactly the canon's four explicitly named call stages frame, examine, prescribe and prognosis once each in order, each with the red-flag opt-out check the canon applies every step of the way, requires pre-call homework drawing on a piece of the signature solution and scheduled within the canon's three-day window, requires the red velvet rope of at least one accept and one reject criterion, requires live payment over a typed method with a positive deposit and is never an observation; `EnrollmentReadinessPolicy` refuses the call before the funnel has passed Funnel Complete. SPEC.md section 12.5 permits it as an explicit stage 8/9 asset, avoiding the named-owner Sell/Enroll stage decision; canon file 06 adds the red velvet rope accept and reject criteria to the seed set. SPEC.md section 12.6 leaves the enumerated six-step process and the dedicated sales/enrollment training absent from the supplied canon, so the shape is extracted from the covered files and recorded as a documented gap. Wiring it into a required stage 8/9 gate kind remains a methodology-owner decision.
- Follow-up and nurture lifecycle (Signature Solution Series, 5P email, re-engagement) — canon 15, 24, 33, 34 — after stage 10 — status: implemented 2026-10-03 (Ralph cycle 111) as the Commercial Design `NurturePlan` (`NurtureAudienceState`, `NurtureModality`, `NurtureMessage`, `NurtureSequence`), which grounds each message on a step of a same-tenant stage 4 `SignatureSolution`, uses the 5P modality (ping is the one-question survey), re-engages non-openers with distinct headlines and binds the sequences to a named owner. SPEC.md section 12.6 warns the dedicated email/follow-up module is absent from the supplied canon, so the shape is extracted from the covered files and recorded as a documented gap; wiring it into a required stage kind remains a named-owner decision.
- Advertising and forecast dashboard (Mastery Advertising Metrics Dashboard, Metrics Matrix) — canon 22, 23, 24 — stage 10 — status: candidate; the cycle 89 production view's `METRICS` reporting dimension is intentionally empty because no context sources metrics yet, so this gap is the named home for that dimension. Cycle 92 captured the optimization discipline (baseline before optimizing, one variable at a time, a logged change) as the Measurement improvement loop, and cycle 93 built the typed metric substrate (`MetricDefinition`, `MeasurementRecord`) the dashboard reads from. Cycle 105 selected populating the production view's `METRICS` dimension from that registry and the improvement loop as the highest priority ready next item, a bounded pure-domain slice of this candidate. Cycle 106 completed that slice: the METRICS dimension now reports each registered metric's newest observed figure and a measured movement via `metric_reporting_views`. Cycle 107 built the canon's forecast equation (`FunnelMetricRole`, `FunnelFigure`, `FunnelEconomics`, `FunnelForecast`, `funnel_figure`) so the metrics matrix unit economics exist before real data and a forecast stays distinct from an observed result.   Cycle 108 built the canon's scaling rule (`LearningPhase`, `ScalingAction`, `ScalingRecommendation`, `AdScalingPolicy`), so the dashboard can now turn an observed cost per lead into an owner-approved scale, hold, bid-up-the-funnel or pause-and-review recommendation. Cycle 109 built the canon's split-test logging (`SplitTestMode`, `SplitTestChange`, `SplitTest`), so a stage 10 optimization logs the one variable it changes (bound to the approved improvement's lever) before reading the result. This candidate is now fully implemented; no remaining scope.
- Audience building and content flywheel (Content Blitz, Content Roadmap, audience campaign, syndication) — canon 25-31 — stages 6 and 10 — status: partially implemented 2026-10-03 (Ralph cycle 115) as the Commercial Design `ContentRoadmap` (`ContentBeat`, `ContentChannel`, `ContentTopic`, `ContentDistributionPolicy`), which maps each step of a same-tenant stage 4 `SignatureSolution` to content topics that follow the Authority Amplifier beat order and reach the canon's minimum blog, YouTube and Facebook channels, binds a named owner and reports the steps it covers and misses. Remaining candidate: the ten-second-view audience campaign, the syndication/recycling schedule and the content measurement loop (canon files 29-31) are delivery and operations assets outside this planning artifact and still need a named-owner decision on where they belong.
- Retargeting system (Retargeting Roadmap, invisible opt-in, banner specs) — canon 33, 34 — stages 8 and 10 — status: implemented 2026-10-03 (Ralph cycle 110) as the Measurement `RetargetingPlan` (`TrackingCode`, `ConversionGoal`, `RetargetingAudience`, `RetargetingCampaign`, `RetargetingChannel`, `RetargetingStep`), which orders the canon's tracking code, conversion goals, retargeting lists and focused campaigns and binds them to one tenant and a named owner; the canon's effective-ads step is covered by the stage 10 `SplitTest` and its metrics step by the `MetricDefinition` registry. Remaining candidate: the canon's invisible opt-in offer and banner-ad spec/swipe-file assets are delivery assets outside this planning artifact and still need a named-owner decision on where they belong.
- Compliance suite (GDPR, disclaimers, privacy, terms) — canon 21, 34 — stage 9 — status: implemented 2026-10-03 (Ralph cycle 94) as the Execution `CompliancePackage` (`ComplianceAssetKind`, `ComplianceAsset`, `ComplianceWaiver`) with the `ComplianceRequiredPolicy` gating `LaunchQA` traffic authorization, so "Launch Approved" needs every required asset or a live owned waiver; projecting the compliance assets onto their own canonical stage 9 gate kind remains a candidate that needs a named-owner decision.
- Positioning and decision tools (Target Market Matchmaker, awareness levels, Funnel Finder) — canon 00, 04, 13, 14 — stages 1 and 2 — status: implemented 2026-10-03 (Ralph cycle 112) for the market awareness levels as the Commercial Design `MarketAwarenessMap` (`MarketAwarenessLevel`), which types the stage 1 `awareness-map` kind with the canon's five levels, requires research evidence and message requirements, rejects a retarget level that is not strictly further down the funnel, and projects to exact `StageAssetVersion` evidence; implemented 2026-10-03 (Ralph cycle 113) for the Target Market Matchmaker as the Commercial Design `TargetMarketCandidate` and `TargetMarketMatchmaker`, which narrows at least two canon-judged candidates to the one to serve now, grounds the chosen market on a same-tenant `MarketAwarenessMap`, and has `TargetMarketMatchPolicy.require_servable` refuse a market whose awareness position is not initially targetable; and implemented 2026-10-03 (Ralph cycle 114) for the Funnel Finder as the Commercial Design `FunnelProfile`, `FunnelType`, `OfferPriceBand` and `FunnelFinder`, which chooses one of the canon's funnel types from the four canon factors, narrows at least two considered types to the selected one with a rationale, and has `FunnelSelectionPolicy.require_price_fit` refuse a high-ticket offer with a self-serve funnel and a low-ticket offer with the sales-call CAC funnel (canon 13, 14). No candidate remains in this gap. Wiring the awareness map, the match or the finder into the `AvatarProfile`, the stage 1 `DiagnosisPackage`, the stage 6 `CampaignMessage` or the stage 8 `FunnelIntegration` is a bounded follow-up; none is a required gate kind yet (a methodology-owner decision).
- Thirteen transformations (the overall shift, three phase shifts and nine step-level from/to pairs, titled from the million dollar message) — canon 09, 10 — stage 4 — status: implemented 2026-10-03 (Ralph cycle 118) as the pure Method `Transformation`, `TransformationScope` and `ThirteenTransformations`, which ground on a same-tenant stage 4 `SignatureSolution`, require exactly one overall shift titled with the Million Dollar Message, three phase shifts and nine step shifts (thirteen total), match each shift's from/to states to the solution's own states, and refuse a missing/extra/duplicate shift, a shift naming a phase or step the solution does not have, a no-op shift and a cross-tenant solution or shift, and never represent the structure as an observation. It is a method structure asset, not a new required stage 4 gate kind; wiring it into the `SignaturePackage` bridge or a required kind remains a bounded follow-up and a methodology-owner decision.
- Umbrella planning (Online Business Launch Map, Bulletproof Business Plan) — canon 00, 01 — over stages 0 to 10 — status: implemented 2026-10-03 (Ralph cycle 116) as the new Portfolio `UmbrellaPlan` (`LaunchMapSection`, `UmbrellaSection`, `BusinessTarget`, `QuarterlyReview`), which binds a named owner, a same-tenant `ClientWorkspace` and a versioned `StageTemplate` to exactly the canon's four launch-map sections (Foundation, Signature Solution, Funnel, Floodgates) covering every template stage exactly once, requires at least one specific measurable business target and an ordered 90-day revisit history, and has `UmbrellaReviewPolicy.require_current` refuse an overdue plan. Mapping the canon's four strategy parts onto stages 0-2/3-5/6-9/10 is a documented intentional deviation from the canon's 12-week calendar. Wiring the plan into the production view or a required gate kind remains a bounded follow-up and a methodology-owner decision.
- Swimlanes channel model — canon 13, 14, 33, 34 — cross-cutting stages 8 to 10 — status: implemented 2026-10-03 (Ralph cycle 117) as the pure Execution `SwimlanesPlan` (`SwimlaneChannel`, `SwimlaneMove`), which types the canon's five channels (messages, ads, human outreach, offline and direct mail, content), maps each stalled funnel step to a distinct next step with a vehicle and one action, grounds on a same-tenant stage 8 `FunnelIntegration`, binds a named owner and reports the channels it covers and misses, and has `SwimlaneCoveragePolicy.require_all_channels` refuse a single-source plan (canon file 34: "you can't be single source dependent"). It lives in Execution because Commercial cannot import the Execution `FunnelIntegration` without a production-commercial-execution import cycle. Wiring it into the production view, the command center or a stage 8/10 kind remains a bounded follow-up and a methodology-owner decision, so it stays a planning asset rather than a required gate kind.
- Missing canon files 19 and 20; promised sales/enrollment and email/follow-up modules absent — status: unresolved, request from license owner.

## Product priority: the gated production engagement

Implement a versioned stage 0 to 10 template from intake through campaign launch. Each stage is a collection of required asset versions, a checkpoint rubric, dependencies, owner, approver, milestone, and gate decision. A task being marked done does not pass its stage. An approved gate pins the exact versions authorized for downstream use. Preserve the distinction between these production stages and the three phase, nine step client Signature Solution.

The first usable vertical slice is stages 0 and 1: establish scope, access and baseline, then produce an approved avatar and diagnosis. Subsequent slices implement currency and Profit Pyramid, method and offer, campaign message and Authority Amplifier, funnel integration and launch QA, then performance baseline and optimization. An existing asset can satisfy a stage only through an evidence and approval review. A waived requirement has a named human risk owner and does not become a fabricated asset.

## Engineering method and delivery gates

Every post fork behavior change uses TDD: write a failing test that expresses a domain or user observable rule, implement the smallest passing behavior, refactor, then run impacted contract and integration suites. Characterize reused upstream behavior before changing it. Each pull request states the bounded context, aggregate invariants, ports, migration effect, security boundary, test evidence, and rollback. Code review rejects domain logic in routes, direct ORM access across contexts, untyped agent outputs, unversioned prompts, and mutations without an authority check.

Test layers: domain unit tests for transitions and policy; application tests with fake ports for commands; adapter contract tests against PostgreSQL, object storage, queue, and model gateway; integration tests with real services; workflow tests for retries, approval waits and resume; browser tests for critical approval and launch paths; security tests for cross client isolation and authority bypass; Helm template validation and deployment smoke tests. Prefer meaningful behavioral tests over implementation mirroring. Keep a small end to end suite and avoid a fragile screenshot gate.

Domain driven design: publish a ubiquitous language glossary, event catalog, context map, aggregate invariants, and ADRs before building new data paths. SOLID and onion enforcement: import rules prevent `domain` from importing `infrastructure`, `api`, framework or model SDK packages; ports are defined by application needs; policy objects remain composable; adapters satisfy contract tests. CI checks formatting, type checking, import boundaries, tests, migration consistency, dependency vulnerabilities, and container/chart validity.

## Phase 0: inspect and establish the fork

Inputs: OpenExecutive repository URL and permissible fork terms, access credentials where required, cluster inventory. Actions: pin upstream commit, inspect code and license, run existing tests, map candidate features to actual modules, document data model and behavior, review secrets, security posture, background execution and existing deployment. Capture baseline test and build results. Create `docs/fork_inventory.md`, context map, ADRs for modular monolith and tenant model, dependency manifest, and a fork diff register. Do not merge domain replacement until the baseline builds locally.

Exit: reproducible local setup, known upstream commit and license, verified reuse matrix, passing baseline or documented existing failures, named owner for each architectural decision. If fork rights or availability fail, pause implementation and choose a clean implementation path through an explicit decision.

## Phase 1: delivery skeleton and authority core

Build: context package boundaries, typed IDs, migrations, tenant scoped repositories, identity and permissions, source record storage, immutable audit trail, outbox, versioned approvals, BuildObject and StageRun state machines, GateDecision, and a seeded versioned 0 to 10 template. Replace generic labels in the UI only after domain semantics exist. Start local containers for dependencies. Add a GitOps staging environment and chart skeleton, without live client data.

TDD examples: approving version A cannot approve version B; writer cannot approve own proposal under a separation policy; tenant A cannot read tenant B's BuildObject; missing asset prevents gate completion; activity without approval leaves stage Working; a scoped waiver records risk owner without creating an asset; illegal state transition returns a named error; audit entry remains after approval is superseded. Implement unit then database integration tests, with security regression tests at HTTP boundary.

Exit: reviewer can create a client workspace, register a traced build, see stage 0 requirements and missing items, request and record an exact version approval, and see an audit trail in staging. Cross client isolation tests pass.

## Phase 2: knowledge and discovery vertical slice

Build: stage 0 intake and baseline capture, stage 1 business and avatar diagnosis, upload and parse supported source formats, checksum and location based citations, claim provenance classes, extraction review, unknowns register, discovery workflow and enterprise brief. Use a client scoped retrieval adapter with measurable recall checks. Preserve original bytes. A RED operator corrects extraction before a client approved diagnosis.

TDD examples: an unsupported fact remains Proposed or Unknown; a claim citation opens the exact source location; conflicting statements are both retained; retrieval cannot cross tenants; parser failure leaves a retryable record without a false success.

Exit: a real pilot source set yields a reviewed, traceable enterprise brief; stage 0 Production Ready and stage 1 Avatar Locked decisions cite exact asset versions. Track extraction correction rate and missing source rate.

## Phase 3: method, offers, and dependency graph

Build: stage 2 primary currency and Million Dollar Message, stage 3 observable Profit Pyramid, stage 4 three phase and nine step Signature Solution, stage 5 Perfect Product; method and offer versioning, transformation milestones, currency and audience fields, approval diff, dependency links, downstream impact analysis. Encode the RED methodology as versioned templates and examples, not as hard coded universal truth. The 3F pilot needs an explicit distinction between existing technical support work and a completed RED method engagement.

TDD examples: currency gate rejects an unspecified audience or unmeasured outcome; pyramid levels require observable differences; offer cannot become production ready without approved method; changing one approved milestone identifies dependent offers and assets; a rejected method proposal does not alter approved version; workflow resumes at the client gate after restart.

Exit: stage 2 Currency Locked, stage 3 Diagnostic Model Approved, stage 4 IP Architecture Locked, and stage 5 Offer Locked have human decisions with the exact approved versions. An upstream change creates a complete review queue.

## Phase 4: asset production and customer journey

Build: stage 6 congruent campaign message, stage 7 Authority Amplifier with script approval before visual production and final creative approval, stage 8 funnel integration, stage 9 three part launch QA; production briefs, template registry, claim check, asset review, release package, customer journey configuration, staging connectors, dry run and launch checklist, incident and rollback records. Implement first the smallest complete pilot journey. Keep external sending or publishing behind a human authorized release action.

TDD examples: campaign message conflicting with the offer blocks approval; visual Authority Amplifier production cannot be authorized by an unapproved script; unsupported proof is flagged; duplicate event does not send duplicate message; failed prospect routing prevents Funnel Complete; failed message, technical or commercial QA prevents Launch Approved; connector timeout creates a visible retry or incident rather than a success state.

Exit: stages 6 through 9 have exact version approvals; one complete 3F journey passes staged customer path tests including opt in, tagging, Authority Amplifier, follow up, qualification, booking, reminders, incomplete assessment, missed appointment and sales handoff. The release has a named human owner, rollback plan, budget decision and acceptance record. Stage 9 shows Ready for Traffic, not live or completed.

## Phase 5: measurement, operations, and portfolio

Build: stage 10 live traffic milestones and baseline, metric registry, event instrumentation, observations and experiment records, command center intervention queries, notification deduplication, health signals, portfolio opportunity register. Track spend, leads, lead cost, page conversion, Authority Amplifier engagement, applications, bookings, shows, closes, acquisition cost, revenue attribution and issues where instrumentation and consent permit. Rank interventions by blocked gate and downstream effects, actual commitments and dependencies, and show evidence behind each recommendation. Use a first improvement cycle to validate whether these views change operator decisions.

TDD examples: launch alone cannot complete the engagement; traffic, lead, qualified appointment and sale are distinct observed milestones; missing baseline blocks a before and after claim; low sample size keeps causal claim as interpretation; stale gate approval produces one owned intervention; dismissal records reason; opportunity remains proposed until investment authority acts.

Exit: stage 10 establishes an evidence backed performance baseline after qualified traffic, with later milestones pending until observed; a performance review records baseline and observed result, one improvement is approved and measured, and operators can resolve a blocked gate from the command center without searching multiple systems. Engagement remains in Optimization until explicit completion criteria are met.

## Phase 6: hardening and production cutover

Perform threat modeling, tenant penetration tests, data export and deletion drill, load tests for expected concurrent workflows, backup and restore exercise, disconnected home network exercise, node restart and worker resume exercise, alert routing and runbook review. Promote images by digest through reviewed GitOps changes. Keep staging and production namespaces, secrets, backups, and database credentials separate. Roll out one RED internal engagement before onboarding additional clients.

Exit: complete security and recovery evidence, production SLO dashboard, named incident owner, signed pilot acceptance, rehearsed rollback, no unresolved high severity access issues. Archive the exact release manifest and prompt versions.

## Sequencing and deliverable ownership

| Sequence | Increment | Depends on | Demonstrable artifact |
| --- | --- | --- | --- |
| 0 | Fork inventory | Upstream access | Reuse matrix and baseline |
| 1 | Authority core | 0 | Approved version with audit |
| 2 | Intake and diagnosis, stages 0 and 1 | 1 | Production Ready and Avatar Locked |
| 3 | Position, model, package, productize, stages 2 through 5 | 2 | Approved currency, diagnostic, method and offer |
| 4 | Message, produce, integrate, QA, stages 6 through 9 | 3 | Approved campaign, creative, funnel and launch readiness |
| 5 | Launch and optimize, stage 10 onward | 4 | Qualified traffic, baseline and improvement cycle |
| 6 | Production cutover | 1 through 5 | Restorable GitOps release |

Do not promise calendar duration before fork and cluster discovery. Estimate each phase after Phase 0 using story slices and staffing, then publish a forecast with confidence ranges. Each increment is usable in isolation and has an explicit acceptance review.

## GitOps and release implementation checklist

Repositories: fork source and separate GitOps environment repository. Branch protection requires code review and CI; images are built once and promoted by immutable digest. Helm values describe staging and production, with no plain secret values in Git. Argo CD owns synchronization. Migration job runs with a scoped account; use expand, migrate, contract changes across releases. Configure health probes, resource limits, network policies, certificate renewal, logs and metrics. Test chart rendering for each environment, policy validation, admission, deployment smoke, rollback and data restore. Document DNS, VPN, registry reachability and the consequences of home power or internet loss.

CI gate order: format and types, domain and application tests, adapter contracts, migration check, API and security tests, frontend checks, image scan and build, Helm lint and render, ephemeral integration test, staged Argo CD reconciliation, smoke test. Production promotion records human approval and produces a Git commit in the GitOps repository. Never treat a green AI response as authorization to deploy.

## Initial backlog by vertical slice

1. Pin upstream commit and record license, environment and component inventory.
2. Write domain glossary, context map, permission matrix and ten ADRs only as decisions arise, with no arbitrary ADR quota.
3. Add tenant boundary and authority tests around forked storage and retrieval.
4. Implement SourceRecord, Claim, approval, decision, BuildObject, StageRun and GateDecision aggregates. [DONE 2026-10-02: Governance `StageGate` + `GateIntegrityPolicy` — missing exact asset version, unapproved dependency, self-approval, and waiver-without-asset all block gate approval; verified by `tests/unit/governance/test_gate_integrity.py`. DONE 2026-10-02 (Ralph cycle 2): version-specific `ApprovalRequest` (exact version + scope, designated approver, expiry) and append-only `Decision` / `DecisionLog`; verified by `tests/unit/governance/test_approval_record.py`. DONE 2026-10-02 (Ralph cycle 3): `StageRun` completes only via an accepted gate for the same stage, never via activity, with `StageStatus` / `StageTransition` and a `StageTransitionPolicy` that rejects illegal transitions; verified by `tests/unit/governance/test_stage_run.py`. DONE 2026-10-02 (Ralph cycle 4): `BuildObject` in the Production context requires an owner and next action while active and rejects illegal lifecycle transitions; verified by `tests/unit/production/test_build_object.py`. DONE 2026-10-02 (Ralph cycle 5): versioned stage 0–10 `StageTemplate` seeded in Governance and `GateIntegrityPolicy` rejects gates that omit a canonical prerequisite, under-declare required asset kinds, or pin a different template version; verified by `tests/unit/governance/test_stage_template.py`. DONE 2026-10-02 (Ralph cycle 6): `StageGate.from_template` derives dependencies, template version and required asset kinds from the canonical template so gate evidence is not self-declared; verified by `tests/unit/governance/test_gate_factory.py`. DONE 2026-10-02 (Ralph cycle 7): immutable `GateDecision` / `GateDisposition` records the stage, pinned required asset versions, checkpoint evidence, reviewer, scope, disposition, rationale and next action, and `GateDecision.from_gate` refuses an approval for a non-approvable gate; verified by `tests/unit/governance/test_gate_decision.py`. DONE 2026-10-02 (Ralph cycle 8): `StageRun.complete` now requires a passing, same-stage, same-template-version `GateDecision` and pins it as immutable `accepted_decision`, replacing the transient `StageGate`; verified by `tests/unit/governance/test_stage_run.py`. DONE 2026-10-02 (Ralph cycle 9): `GateLedger` derives prerequisite state from durable `GateDecision`s and refuses a passing decision while a prerequisite stage lacks a passing decision, so the dependency map is no longer caller-supplied; verified by `tests/unit/governance/test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 10): `GateDecision.from_gate` now requires a `GateLedger` and reads prerequisite state and the canonical template only from the ledger, removing the caller-supplied `dependency_states` map from the decision boundary; verified by `tests/unit/governance/test_gate_decision.py` and `test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 11): Knowledge `SourceRecord` (frozen original: locator, checksum, capture time, access rule; `cite` returns a checksum-pinned citation) and `Claim` (statement, `Known`/`Derived`/`Proposed`/`Unknown`, citations, confidence note) with `reclassify` records an audited `ClaimRevision`, refuses `Known` without a direct citation, and preserves the original so Derived/Proposed never silently become Known; verified by `tests/unit/knowledge/test_source_record.py` and `test_claim.py`. DONE 2026-10-02 (Ralph cycle 12): Method `SemanticVersion` / `MethodVersion` / `MethodApproval` pin an exact semantic version and intended use, revisions must advance the version and drop the old approval, and `MethodChangeImpactPolicy` emits an owned review queue (offer, brief, asset, journey, claim with human owner and due date) for a change to an approved method, rejecting unapproved or non-advancing or cross-tenant changes; verified by `tests/unit/method/test_method_version.py` and `test_method_impact.py`. DONE 2026-10-02 (Ralph cycle 13): Commercial Design `MethodReference` / `OfferVersion` records audience, promise, eligibility, price hypothesis and at least one exact method reference, and `OfferReadinessPolicy` refuses production readiness unless every reference is an approved `MethodVersion` of the same tenant at the exact version and intended use; `mark_review_required` drops readiness after an upstream change and a terminal offer cannot be revived; verified by `tests/unit/commercial/test_offer_version.py`. DONE 2026-10-02 (Ralph cycle 15): `GateLedger.record` refuses a passing `GateDecision` whose pinned asset kinds do not exactly match the canonical `StageTemplate` required package for the stage (under-declared or substituted), closing the durable boundary previously checked only at the `from_gate` factory; ledger fixtures now use canonical kinds; verified by `tests/unit/governance/test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 16): `GateIntegrityPolicy._template_reasons` now applies the same exact asset-package rule as the durable ledger, rejecting a gate that declares a non-canonical extra asset kind as well as one that omits a canonical kind, so `GateDecision.from_gate` can no longer produce a passing decision the `GateLedger` must refuse and gate evaluation and durable recording are consistent; verified by `tests/unit/governance/test_stage_template.py`. DONE 2026-10-02 (Ralph cycle 18): `GateDecision` now persists the assigned work owner and due date for every stage and rejects a decision that omits either, closing the SPEC.md section 4 gate-record gap where the production view must answer who is accountable and when the next approval is due; verified by `tests/unit/governance/test_gate_decision.py` (with `from_gate` factory passthrough). DONE 2026-10-02 (Ralph cycle 20): `StageGate` and `GateDecision` now pin the canonical checkpoint rubric derived from `StageDefinition.checkpoint`, and `GateLedger` and `GateIntegrityPolicy` reject a passing gate or decision whose checkpoint differs from the template, closing the last SPEC.md section 4 gate-record field; verified by `tests/unit/governance/test_gate_checkpoint.py`. DONE 2026-10-02 (Ralph cycle 32): a passing `GateDecision` and an approvable `StageGate` must pin exactly one exact version per required asset kind; an ambiguous multi-version package (for example two versions of `authority-amplifier-script`) is refused by `GateDecision.__post_init__`, `GateIntegrityPolicy.evaluate` and `GateLedger.record` via the new `duplicate_asset_kinds` helper and `AmbiguousAssetPackageError`, so the exact asset pin required by SPEC.md sections 3 and 4 cannot be defeated by a package that identifies no single approved version; verified by `tests/unit/governance/test_gate_asset_exactness.py`. DONE 2026-10-02 (Ralph cycle 34): a passing `GateDecision` now pins the durable per-asset `ApprovalRequest`s and refuses construction unless every pinned asset version is covered by an approved, in-scope, unexpired request, so a self-declared approved asset set can no longer pass a gate and a stage cannot complete without a recorded per-asset approval; `GateDecision.from_gate` takes the approvals and `UnapprovedAssetError` names the uncovered versions; verified by `tests/unit/governance/test_asset_approval.py` and the updated governance fixtures. DONE 2026-10-02 (Ralph cycle 35): `StageGate.approved_assets` is now a derived, read-only set evidenced by recorded version-specific `ApprovalRequest`s (`record_asset_approval` refuses an approval outside the pinned package and another version does not evidence the asset), so `GateIntegrityPolicy` evaluates the same recorded evidence a passing `GateDecision` pins and the self-managed field cannot be assigned; verified by `tests/unit/governance/test_gate_asset_evidence.py`. DONE 2026-10-02 (Ralph cycle 36): `GateDecision.from_gate` records the gate's own `asset_approvals` and no longer accepts a caller-supplied approval set, so a passing decision can only pin the evidence the gate recorded and the policy evaluated; the decision validates that evidence against its own scope and date and refuses a gate whose recorded approvals do not cover the decision scope; verified by `tests/unit/governance/test_gate_asset_evidence.py` with updated fixtures in `test_asset_approval.py`, `test_gate_decision.py`, `test_gate_ledger.py` and `test_gate_checkpoint.py`. DONE 2026-10-02 (Ralph cycle 37): `StageGate.approved_assets`/`missing_assets`/`authorizes_downstream` and `GateIntegrityPolicy.evaluate` now require an explicit evaluation instant and treat an approval already expired at that instant as not evidencing its asset, so the gate and the policy agree with the durable `GateDecision`'s expiry check; verified by `tests/unit/governance/test_gate_asset_evidence.py` (`GateApprovalExpiryTests`). DONE 2026-10-02 (Ralph cycle 38): `StageGate.approved_assets`/`missing_assets`/`authorizes_downstream` and `GateIntegrityPolicy.evaluate` now take the intended downstream scope and derive evidenced assets through `ApprovalRequest.authorizes`, and `GateDecision.from_gate` threads its scope into the policy and gate, so the gate, policy and durable decision agree on version, scope and expiry; verified by `tests/unit/governance/test_gate_asset_evidence.py` (`GateApprovalScopeTests`). DONE 2026-10-02 (Ralph cycle 39): `GateDecision` exposes `unapproved_assets_at(on)`/`authorizes_downstream_at(on)`, `GateLedger.has_passing_decision`/`dependency_states` take a required `on` instant and report a passing prerequisite whose pinned approvals have expired as `BLOCKED`, and `GateLedger.record`/`GateDecision.from_gate` plus `PipelineProgress.from_ledger` evaluate at that instant, so "a failed or expired prerequisite blocks dependent authorization until resolved" holds across the dependency graph; verified by `tests/unit/governance/test_gate_prerequisite_expiry.py`. DONE 2026-10-02 (Ralph cycle 41): `GateLedger.has_passing_decision(stage, on=...)` and `dependency_states` now traverse the template's prerequisite chain transitively, so a stage whose own approvals are current is not reported passing while any upstream stage has lapsed; `dependency_states` reports every stage behind an expired chain as `BLOCKED` and `PipelineProgress.from_ledger` stops counting those gates, closing the transitive half of the SPEC.md section 4 rule; verified by `tests/unit/governance/test_gate_prerequisite_expiry.py` (`GateLedgerTransitivePrerequisiteExpiryTests`). DONE 2026-10-02 (Ralph cycle 43): `StageRun.complete` now requires the accepted `GateDecision` to be the stage's current durable `GateLedger` decision (by identity) before transitioning, so a transient passing decision the ledger never recorded, or an earlier pass later superseded by a durable non-passing entry, can no longer complete a stage; verified by `tests/unit/governance/test_stage_run.py` (`StageCompletionDurabilityTests`). DONE 2026-10-02 (Ralph cycle 44): `Waiver` requires a non-empty set of `downstream_effects` of non-blank identifiers, so a waivered `GateDecision` records the concrete downstream stages/assets/journeys it affects rather than acting as a blanket bypass; verified by `tests/unit/governance/test_gate_decision.py` (`WaiverScopeTests`). DONE 2026-10-02 (Ralph cycle 45): `GateDecision.__post_init__` now requires a waived decision to name a non-blank intended downstream `scope` and refuses any `Waiver.downstream_effects` outside that scope, so a waiver cannot claim an impact surface broader than the gate it decided; verified by `tests/unit/governance/test_gate_decision.py` (`WaiverDecisionScopeTests`). DONE 2026-10-02 (Ralph cycle 46): `GateDecision.from_gate` now requires a waived disposition to name the gate's designated approver as its reviewer, refuses a waiver recorded by any other actor, refuses a gate with no designated approver, and refuses the gate's author waiving their own gate, so a waiver is a real human authority decision rather than a self-issued bypass of a missing asset; verified by `tests/unit/governance/test_gate_decision.py` (`WaiverAuthorityTests`). DONE 2026-10-02 (Ralph cycle 47): `GateDecision.__post_init__` now requires every disposition — not only a passing one — to pin a non-empty required asset package with exactly one exact version per kind, so a BLOCKED, CHANGES_REQUIRED, WAIVED or SUPERSEDED decision cannot hide the exact versions at issue behind its disposition; verified by `tests/unit/governance/test_gate_asset_exactness.py` (`GateDecisionAssetPackageRequiredTests`). DONE 2026-10-02 (Ralph cycle 48): `GateLedger.record` enforces the canonical required asset kinds and canonical checkpoint for every `GateDecision` disposition, so a BLOCKED, CHANGES_REQUIRED, WAIVED or SUPERSEDED decision cannot contradict the template the production view derives requirements from; verified by `tests/unit/governance/test_gate_ledger_canonical_package.py`. DONE 2026-10-02 (Ralph cycle 53): `GateDecision.__post_init__` now refuses to record a `WAIVED` decision whose scoped `Waiver` is already expired at `decided_on`, so the durable record and the `StageRun` mirror agree that a lapsed risk acceptance is never a current disposition and the production view cannot read an expired waiver as live; verified by `tests/unit/governance/test_gate_decision.py` (`WaiverExpiryDecisionTests`). Remaining: SourceRecord, Claim, MethodVersion and OfferVersion repository adapters remain blocked on the storage ADR.]
5. Implement stages 0 and 1 from intake to approved avatar and diagnosis. [DONE 2026-10-02 (Ralph cycle 54): Commercial Design `AvatarProfile` is a frozen reject-only value object requiring the stage 1 avatar's demographics, psychographics, pains, goals, consequences of inaction, awareness, customer evidence and voice notes, so the "Avatar Locked" checkpoint ("a stranger can recognize who the customer is, what matters, and why now") is met by a real asset; `AvatarLockedPolicy.require_locked` refuses to lock an avatar whose customer evidence is not a same-tenant, known, directly sourced Knowledge claim; verified by `tests/unit/commercial/test_avatar_profile.py`. DONE 2026-10-02 (Ralph cycle 55): Commercial Design `BusinessSnapshot` and `OfferFunnelAudit` are frozen reject-only value objects requiring the stage 1 diagnosis current-state and audit packages (business model, current offers, lead sources, constraints, narrative; offer findings, funnel steps, conversion evidence, gaps, narrative) and recording the Knowledge claim ids that evidence them, and `DiagnosisEvidencePolicy` refuses to evidence either asset with an unsourced, derived, proposed, foreign or absent claim, so all three stage 1 asset kinds are now real, source-checked values; the shared `sourced_claim_ids` helper also backs `AvatarLockedPolicy`; verified by `tests/unit/commercial/test_diagnosis_assets.py`. DONE 2026-10-02 (Ralph cycle 56): Engagement `ClientWorkspace` is the stage 0 tenant root named in the SPEC.md section 3 aggregate table, requiring an opaque id, tenant and duplicate-free named-authority registry and enforcing "every child resource belongs to exactly one client" by refusing a blank child, a duplicate attachment and a foreign-tenant child; it records the engagement lifecycle from SPEC.md section 4 with a forward-only canonical progression, pause/resume and terminal Completed, recording actor, reason, timestamp, old/new state and correlation id; DONE 2026-10-02 (Ralph cycle 57): Engagement `IntakeAssetKind`, `IntakeAsset` and `IntakePackage` are frozen reject-only values for the full stage 0 "Intake" package, the kind list provably matches the canonical stage 0 template, a package rejects a duplicate kind and a foreign-tenant asset and reports its missing kinds, and `ProductionReadyPolicy` refuses an incomplete package, an asset owner who is not a designated workspace authority, and evidence that is not a known, directly sourced, same-tenant claim; the `sourced_claim_ids` rule moved to `knowledge/domain/policies.py` and is now shared with commercial; verified by `tests/unit/engagement/test_intake_package.py`. DONE 2026-10-02 (Ralph cycle 58): Governance `StageAssetVersion` represents a real stage asset at one exact version (unique id, owning tenant, canonical kind, positive version) and `pin(tenant_id=...)` maps it to an `AssetVersionRef(keyed by kind)` while refusing a version-less asset (`VersionlessAssetError`) and a cross-tenant asset (`CrossTenantAssetError`), and the pinned refs build a canonical `StageGate.from_template` package; verified by `tests/unit/governance/test_asset_version_pin.py`. DONE 2026-10-02 (Ralph cycle 59): Governance `StageGate.from_assets(template, stage_number, *, tenant_id, assets)` assembles a stage's canonical gate from real `StageAssetVersion`s, pinning each for the workspace tenant so a cross-tenant asset (`CrossTenantAssetError`), a second version of one kind (`AmbiguousAssetPackageError`), a missing or extra canonical kind (`AssetPackageMismatchError`) and an unknown stage (`UnknownStageError`) are all refused instead of silently pinned; verified by `tests/unit/governance/test_stage_asset_package.py`. The new finding is that the Engagement stage 0 `IntakeAsset` still carries no typed exact version, so a complete package cannot yet yield the assets `from_assets` pins; that bridge is the highest priority ready next item. DONE 2026-10-02 (Ralph cycle 59): Engagement stage 0 `IntakeAsset` now carries a typed positive integer `version` (rejecting a versionless or non-positive asset) and a `canonical_kind` equal to the governance template asset kind, and `IntakePackage.stage_asset_versions()` projects the package's real assets onto governance `StageAssetVersion`s; a complete twelve-kind package assembles the canonical stage 0 gate via `StageGate.from_assets` and a partial package is refused by `AssetPackageMismatchError`; verified by `tests/unit/engagement/test_intake_package.py`. DONE 2026-10-02 (Ralph cycle 61): Engagement `GateApproverAuthorityPolicy.require(gate, workspace)` refuses a stage gate whose designated approver is absent or is not a named authority on the `ClientWorkspace`, raising `GateApproverNotAuthorizedError`, so a stage gate (including stage 0 "Production Ready") can only be approved by a client-designated human; it checks against the gate's own workspace and never invents a concrete approver identity or authority role; verified by `tests/unit/engagement/test_gate_approver_authority.py`. DONE 2026-10-02 (Ralph cycle 62): Engagement `StageZeroGateAssembler` composes `ProductionReadyPolicy`, `StageGate.from_assets` and `GateApproverAuthorityPolicy` so a stage 0 gate is handed downstream only when the intake package is complete, every asset owner is a named workspace authority, every asset is evidenced by a same-tenant directly sourced claim, the gate pins the template's exact twelve asset versions, and the designated approver is a named workspace authority; verified by `tests/unit/engagement/test_stage_zero_gate_assembly.py`. DONE 2026-10-02 (Ralph cycle 63): Engagement `StageZeroGateRecorder.record` closes the stage 0 "Production Ready" checkpoint end to end in pure domain: it takes the `StageZeroGateAssembler` output, issues and approves one exact-version `ApprovalRequest` per required asset (twelve) through the workspace's designated approver, refuses a gate for another stage (`NotStageZeroGateError`), a gate with no author (`GateAuthorRequiredError`), an absent or non-authority approver (`GateApproverNotAuthorizedError`) and a self-approving author (`SelfApprovalError`), records the immutable passing `GateDecision` in a `GateLedger`, and lets `PipelineProgress` report one approved gate; an under-declared asset package is still refused by `GateDecision.from_gate`/the ledger; verified by `tests/unit/engagement/test_stage_zero_gate_recording.py`. DONE 2026-10-02 (Ralph cycle 64): Engagement's first application use case `RecordStageZeroGateHandler` (with typed `RecordStageZeroGateCommand`) composes `StageZeroGateAssembler` and `StageZeroGateRecorder` so the canonical stage 0 "Production Ready" gate is built from the real `IntakePackage` at the application boundary; a caller cannot hand the recorder a hand-built gate, so `ProductionReadyPolicy` owner-authority and sourced-evidence checks cannot be bypassed, and the use case records a passing exact-version decision for all twelve assets (or lands nothing when a package, owner, evidence source or approver is invalid); verified by `tests/unit/engagement/test_record_stage_zero_gate.py`. DONE 2026-10-02 (Ralph cycle 65): the same `RecordStageZeroGateHandler` now closes the stage 0 `StageRun` from the durable ledger decision in one atomic application operation, so a passing `GateDecision` can no longer be written while the stage stays open and `PipelineProgress` (approved gates) and stage status agree; `RecordStageZeroGateCommand` carries the stage 0 `StageRun` and a correlation id, a run for another stage or template version is refused (`StageRunNotStageZeroError`), and a Not Started/Changes Required/Blocked/Waived/Complete/Superseded run is refused before any decision is written (`StageRunNotCompletableError`); verified by `tests/unit/engagement/test_record_stage_zero_gate.py`. The stage 1 gate wiring and the stage 1 nine-kind/three-asset representation mismatch remain, the latter the top named-owner blocker. DONE 2026-10-03 (Ralph cycle 69): the nine-kind/three-asset mismatch is resolved by a pure Commercial `DiagnosisPackage` that projects the three reviewed stage 1 values onto the nine canonical kinds as exact `StageAssetVersion` evidence, so the projected assets assemble a canonical stage 1 gate via `StageGate.from_assets`; verified by `tests/unit/commercial/test_diagnosis_package.py`. Stage 1 gate wiring is now the top ready next item. DONE 2026-10-03 (Ralph cycle 70): the stage 1 "Avatar Locked" gate is wired end to end with Engagement `StageOneGateAssembler` (validates the `DiagnosisPackage` with `AvatarLockedPolicy` and `DiagnosisEvidencePolicy`, pins the canonical gate via `StageGate.from_assets`, binds the approver to the workspace), `StageOneGateRecorder` (one approved exact-version request per kind and the durable passing `GateDecision`, refusing a foreign stage, absent author, unauthorized approver or unaccountable owner), `RecordStageOneGateCommand` and `RecordStageOneGateHandler` (closes the stage 1 `StageRun` from the durable decision, refusing a run for another stage or version and a not-completable run; governance refuses the pass until stage 0 has passed); verified by `tests/unit/engagement/test_record_stage_one_gate.py` (26 tests). Stage 1 can now close, so stage 2 "Currency Locked" is unblocked.]
6. Implement stages 2 and 3 from primary currency to observable Profit Pyramid. [DONE 2026-10-02 (Ralph cycle 17): Method `PrimaryCurrency` value object requires a specific audience, distinct current/desired measures, and a distinct mechanism, rejecting an unspecified person or unmeasured outcome, so the stage 2 "Currency Locked" checkpoint rule is met by a real domain value; verified by `tests/unit/method/test_primary_currency.py`. DONE 2026-10-02 (Ralph cycle 19): Method `ProfitPyramidLevel` and `DiagnosticModel` require each level's observable measures, symptoms, behaviors and problems and reject adjacent levels that cannot be told apart by an observable difference, so the stage 3 "Diagnostic Model Approved" checkpoint rule is met by a real domain value; verified by `tests/unit/method/test_diagnostic_model.py`. DONE 2026-10-02 (Ralph cycle 21): `MethodVersion` pins the exact tenant-checked stage 2 `PrimaryCurrency` and stage 3 `DiagnosticModel`, refuses approval without both pins, rejects a cross-tenant pin, and drops both pins on `revised`; verified by `tests/unit/method/test_method_dependencies.py`. DONE 2026-10-03 (Ralph cycle 71): Commercial `CurrencyInventory`, `PositioningDecision`, `MillionDollarMessage` and the `CurrencyPackage` bridge (canon 04, 05, 06) project the four reviewed stage 2 values onto the ten canonical stage 2 kinds as exact   `StageAssetVersion` evidence, refusing a blank identity, a versionless asset or a cross-tenant value, so the stage 2 "Currency Locked" gate can now be assembled; verified by `tests/unit/commercial/test_currency_package.py` (22 tests). DONE 2026-10-03 (Ralph cycle 72): Engagement `StageTwoGateAssembler`, `StageTwoGateRecorder`, `RecordStageTwoGateCommand` and `RecordStageTwoGateHandler` wire the stage 2 "Currency Locked" `GateDecision` end to end, binding the reviewed `CurrencyPackage` to the workspace tenant and authority registry, issuing one exact-version approval per required kind, writing the durable decision, and closing the stage 2 `StageRun`; stage 2 depends on stage 1, so the ledger must already hold a passing stage 1 decision; verified by `tests/unit/engagement/test_record_stage_two_gate.py` (22 tests). DONE 2026-10-03 (Ralph cycle 73): Commercial `DiagnosticPackage` bridge (canon 07, 08) completes the Method `DiagnosticModel` with the SPEC-required `visual` and `explanatory_copy` and projects the reviewed model onto the ten canonical stage 3 kinds as exact `StageAssetVersion` evidence, so the stage 3 "Diagnostic Model Approved" gate can now be assembled; verified by `tests/unit/commercial/test_diagnostic_package.py` (10 tests) plus two `DiagnosticModel` field tests. DONE 2026-10-03 (Ralph cycle 74): Engagement `StageThreeGateAssembler`, `StageThreeGateRecorder`, `RecordStageThreeGateCommand` and `RecordStageThreeGateHandler` wire the stage 3 "Diagnostic Model Approved" `GateDecision` end to end, binding the reviewed `DiagnosticPackage` to the workspace tenant and authority registry, issuing one exact-version approval per required kind, writing the durable decision, and closing the stage 3 `StageRun`; stage 3 depends on stage 2, so the ledger must already hold a passing stage 2 decision; verified by `tests/unit/engagement/test_record_stage_three_gate.py` (22 tests). DONE 2026-10-03 (Ralph cycle 75): Commercial `SignaturePackage` bridge (canon 09, 10) projects the reviewed Method `SignatureSolution` onto the twelve canonical stage 4 kinds as exact `StageAssetVersion` evidence, so the stage 4 "IP Architecture Locked" gate can now be assembled; verified by `tests/unit/commercial/test_signature_package.py` (10 tests). The stage 4 `GateDecision` wiring remains.]
7. Implement stages 4 and 5 from grounded Signature Solution to offer approval. [DONE 2026-10-02 (Ralph cycle 14): commercial `OfferVersion` requires an accountable owner and `OfferChangeImpactPolicy` discovers dependent offers from an approved method change and marks them review required, so the SPEC.md section 11 "changing a method version identifies dependents" acceptance test is met by a real aggregate; verified by `tests/unit/commercial/test_offer_change_impact.py`. DONE 2026-10-02 (Ralph cycle 22): Method `SignatureStep`, `TransformationPhase` and frozen `SignatureSolution` require exactly three phases and nine steps, a process inventory, transformation map, narrative and visual, one continuous chain of named stages, and declared starting/final states that are the ends of that chain, so the stage 4 "IP Architecture Locked" checkpoint rule is met by a real domain value; verified by `tests/unit/method/test_signature_solution.py`. DONE 2026-10-02 (Ralph cycle 23): `MethodVersion` pins the exact tenant-checked stage 4 `SignatureSolution`, refuses approval without it, rejects a cross-tenant pin, and drops the pin on `revised`, so an approved method must carry its locked stage 4 structure; verified by `tests/unit/method/test_method_dependencies.py`. DONE 2026-10-02 (Ralph cycle 24): commercial `StepDelivery` and `DeliverySpecification` require every locked stage 4 method step to carry an action, actor, deliverable, timing and measure, record the full stage 5 asset package, and reject a missing or extra method step, a duplicate delivery, a foreign-tenant method or step delivery, and any missing package field, so the stage 5 "Offer Locked" checkpoint rule is met by a real value; verified by `tests/unit/commercial/test_delivery_specification.py`. DONE 2026-10-02 (Ralph cycle 25): `OfferVersion` pins the tenant-checked stage 5 `DeliverySpecification`, refuses production readiness without it, and `revised` drops the delivery specification and readiness (including when the method reference changes) so an approved offer must carry a complete stage 5 delivery package; verified by `tests/unit/commercial/test_offer_version.py` with a shared fixture in `tests/unit/commercial/fixtures.py`. DONE 2026-10-02 (Ralph cycle 26): `OfferReadinessPolicy` refuses production readiness when the stage 5 `DeliverySpecification.signature_solution` is not equal to the `SignatureSolution` pinned by an approved method reference, so a stage 5 package cannot describe a different transformation than the approved stage 4 method; verified by `tests/unit/commercial/test_offer_version.py`. DONE 2026-10-03 (Ralph cycle 76): Engagement `StageFourGateAssembler`, `StageFourGateRecorder`, `RecordStageFourGateCommand` and `RecordStageFourGateHandler` wire the stage 4 "IP Architecture Locked" `GateDecision` end to end, binding the reviewed `SignaturePackage` to the workspace tenant and authority registry, issuing one exact-version approval per required kind, writing the durable decision, and closing the stage 4 `StageRun`; stage 4 depends on stage 3, so the ledger must already hold a passing stage 3 decision; verified by `tests/unit/engagement/test_record_stage_four_gate.py` (22 tests). DONE 2026-10-03 (Ralph cycle 77): the Commercial `OfferPackage` bridge (canon 11, 12) projects the reviewed stage 5 `DeliverySpecification` onto the twelve canonical kinds as exact `StageAssetVersion` evidence; verified by `tests/unit/commercial/test_offer_package.py` (10 tests). DONE 2026-10-03 (Ralph cycle 78): Engagement `StageFiveGateAssembler`, `StageFiveGateRecorder`, `RecordStageFiveGateCommand` and `RecordStageFiveGateHandler` wire the stage 5 "Offer Locked" `GateDecision` end to end, binding the reviewed `OfferPackage` to the workspace tenant and authority registry, issuing one exact-version approval per required kind, writing the durable decision, and closing the stage 5 `StageRun`; stage 5 depends on stage 4, so the ledger must already hold a passing stage 4 decision; verified by `tests/unit/engagement/test_record_stage_five_gate.py` (22 tests). The stage 6 reviewed-asset bridge remains.]
8. Implement stages 6 and 7 with message congruence and script approval before creative production. [DONE 2026-10-02 (Ralph cycle 27): commercial `CampaignMessage` records the stage 6 asset package, requires each message field, and rejects a cross-tenant offer at construction; `CampaignMessageAlignmentPolicy` refuses the "Campaign Message Approved" checkpoint unless the message is grounded on a production ready stage 5 offer and its avatar, promise, product, method, currency and problem agree with the offer and the approved method's locked stage 2 primary currency and stage 3 diagnostic model, so Phase 4's "campaign message conflicting with the offer blocks approval" example is met by a real aggregate; verified by `tests/unit/commercial/test_campaign_message.py`. DONE 2026-10-02 (Ralph cycle 28): Production `AuthorityAmplifier` records the canonical Promise, Proof, Problems, Steps, Context, Action script and the full stage 7 visual/video package, requires at least one proof claim, and rejects a cross-tenant stage 6 message at construction; `AuthorityAmplifierPolicy` refuses script approval unless the message is approved and the method is an approved dependency, and flags proof claims not backed by a known, directly sourced Knowledge claim; visual production and creative acceptance both refuse before script approval and creative acceptance also requires the complete visual package, so Phase 4's "visual Authority Amplifier production cannot be authorized by an unapproved script" and "unsupported proof is flagged" examples are met by a real aggregate; verified by `tests/unit/production/test_authority_amplifier.py`. Stage 7 wiring into a governance `GateDecision` remains, blocked on the asset-version representation decision.] DONE 2026-10-03 (Ralph cycle 79): built the Commercial `CampaignMessagePackage` bridge (canon-informed, SPEC.md section 12.3 stage 6 files 06, 15, 24, 25-28) projecting the reviewed stage 6 `CampaignMessage` onto the twelve canonical stage 6 kinds as exact `StageAssetVersion` evidence; verified by `tests/unit/commercial/test_campaign_message_package.py` (10 tests), so the stage 6 gate is now assembleable. DONE 2026-10-03 (Ralph cycle 80): wired the stage 6 "Campaign Message Approved" `GateDecision` end to end with `StageSixGateAssembler`, `StageSixGateRecorder`, `RecordStageSixGateCommand` and `RecordStageSixGateHandler`, plus named errors `NotStageSixGateError`, `StageRunNotStageSixError` and `CampaignMessageNotApprovedError`, refusing an unapproved message so the congruence checkpoint cannot be bypassed, binding the reviewed `CampaignMessagePackage` to the workspace tenant and authority registry and closing the stage 6 `StageRun` from the durable decision; verified by `tests/unit/engagement/test_record_stage_six_gate.py` (24 tests), so stage 6 can now close. DONE 2026-10-03 (Ralph cycle 81): built the Production `AuthorityAmplifierPackage` bridge (canon-informed, SPEC.md section 12.3 stage 7 files 13-18, 28) projecting the reviewed stage 7 `AuthorityAmplifier` onto the nine canonical stage 7 kinds as exact `StageAssetVersion` evidence and refusing an amplifier without its visual package, so the stage 7 gate is now assembleable; verified by `tests/unit/production/test_authority_amplifier_package.py` (12 tests). DONE 2026-10-03 (Ralph cycle 82): wired the stage 7 "Authority Amplifier Approved" `GateDecision` end to end with `StageSevenGateAssembler`, `StageSevenGateRecorder`, `RecordStageSevenGateCommand` and `RecordStageSevenGateHandler`, plus named errors `NotStageSevenGateError`, `StageRunNotStageSevenError` and `AuthorityAmplifierNotApprovedError`, refusing an amplifier without final creative acceptance (the second of the two stage 7 approvals) so the checkpoint cannot be bypassed, binding the reviewed `AuthorityAmplifierPackage` to the workspace tenant and authority registry and closing the stage 7 `StageRun` from the durable decision; verified by `tests/unit/engagement/test_record_stage_seven_gate.py` (24 tests), so stage 7 can now close and stage 8 is unblocked pending its reviewed-asset bridge.
9. Implement stages 8 and 9 with complete prospect path and three part QA. [DONE 2026-10-02 (Ralph cycle 29): Execution `FunnelIntegration` records the complete stage 8 asset package, is grounded on the approved stage 7 `AuthorityAmplifier`, and rejects a cross-tenant amplifier at construction; `FunnelCompletionPolicy` refuses "Funnel Complete" unless the amplifier has creative acceptance and a same-tenant `ProspectPathDryRun` routed every capture, engagement and conversion handoff exactly once with a reliable record and named owner, so Phase 4's "failed prospect routing prevents Funnel Complete" example is met by a real aggregate; verified by `tests/unit/execution/test_funnel_integration.py`. DONE 2026-10-02 (Ralph cycle 30): Execution `LaunchQA` records the full stage 9 check set, requires an owner and a designated human authority distinct from the owner, is grounded on the completed stage 8 `FunnelIntegration`, and rejects a cross-tenant funnel at construction; `LaunchApprovedPolicy` refuses "Launch Approved" unless the funnel is complete, every canonical check is present, every critical-path check passed (payment and dashboard may be excepted with a named owner), and the designated authority authorizes traffic, and `TrafficAuthorization` reports readiness rather than live traffic, so Phase 4's "failed message, technical or commercial QA prevents Launch Approved" example is met by a real aggregate; verified by `tests/unit/execution/test_launch_qa.py`. Stage 8 and 9 wiring into a governance `GateDecision` remain, blocked on the asset-version representation decision. DONE 2026-10-03 (Ralph cycle 83): built the Execution `FunnelIntegrationPackage` bridge (canon-informed, SPEC.md section 12.3 stage 8 files 13, 14, 21, 22) projecting the reviewed stage 8 `FunnelIntegration` onto the thirteen canonical stage 8 kinds as exact `StageAssetVersion` evidence and refusing a funnel that has not passed Funnel Complete; verified by `tests/unit/execution/test_funnel_integration_package.py` (12 tests), so the stage 8 "Funnel Complete" gate is now assembleable and its `GateDecision` wiring is the next step. DONE 2026-10-03 (Ralph cycle 84): wired the stage 8 "Funnel Complete" `GateDecision` end to end with `StageEightGateAssembler`, `StageEightGateRecorder`, `RecordStageEightGateCommand` and `RecordStageEightGateHandler`, plus named errors `NotStageEightGateError` and `StageRunNotStageEightError` (canon-informed, SPEC.md section 12.3 stage 8 files 13, 14, 21, 22), binding the reviewed `FunnelIntegrationPackage` to the workspace tenant and authority registry, issuing one exact-version approval per canonical kind and closing the stage 8 `StageRun`; verified by `tests/unit/engagement/test_record_stage_eight_gate.py` (22 tests), so stage 8 can now close and stage 9 is unblocked pending its reviewed-asset bridge. DONE 2026-10-03 (Ralph cycle 85): built the Execution `LaunchQAPackage` bridge (canon-informed, SPEC.md section 12.3 stage 9 files 01, 08, 21, 22, 24) projecting the reviewed stage 9 `LaunchQA` onto the sixteen canonical stage 9 kinds as exact `StageAssetVersion` evidence, with a `CANONICAL_LAUNCH_KIND_CHECKS` map covering every `QACheckKind` exactly once and refusing a QA that has not passed Launch Approved; verified by `tests/unit/execution/test_launch_qa_package.py` (13 tests), so the stage 9 "Launch Approved" gate is now assembleable and its `GateDecision` wiring is the next step. DONE 2026-10-03 (Ralph cycle 86): wired the stage 9 "Launch Approved" `GateDecision` end to end with `StageNineGateAssembler`, `StageNineGateRecorder`, `RecordStageNineGateCommand` and `RecordStageNineGateHandler`, plus named errors `NotStageNineGateError` and `StageRunNotStageNineError` (canon-informed, SPEC.md section 12.3 stage 9 files 01, 08, 21, 22, 24), binding the reviewed `LaunchQAPackage` to the workspace tenant and authority registry, issuing one exact-version approval per canonical kind and closing the stage 9 `StageRun`; verified by `tests/unit/engagement/test_record_stage_nine_gate.py` (22 tests), so stage 9 can now close and the stage 10 reviewed-asset bridge is the next step. DONE 2026-10-03 (Ralph cycle 94): built the Execution stage 9 launch compliance and consent package (`ComplianceAssetKind`, `ComplianceAsset`, `ComplianceWaiver`, `CompliancePackage`, `ComplianceRequiredPolicy`; canon-informed, SPEC.md section 12.3 stage 9 files 21 and 34 and section 4 "consent where applicable") and wired it into `LaunchQA.authorize_traffic`, so the "Launch Approved" checkpoint refuses traffic when a required compliance asset is absent or its waiver has expired, and a ready QA now necessarily pins its reviewed package; verified by `tests/unit/execution/test_compliance_package.py` (25 tests), so the launch gate now enforces the canon compliance suite without adding a canonical gate kind.]
10. Implement stage 10 baseline, command center and improvement loop. [DONE 2026-10-02 (Ralph cycle 31): Execution `PerformanceBaseline` records the full stage 10 asset package and the distinct first-qualified-traffic, lead, appointment and sale milestones as observed or pending, is grounded on the stage 9 `LaunchQA`, and rejects a cross-tenant QA or milestone at construction; `PerformanceBaselinePolicy` refuses "Performance Baseline Established" unless the launch QA is `READY_FOR_TRAFFIC`, every canonical milestone is recorded, and first qualified traffic is observed, so Phase 5's "launch alone cannot complete the engagement" example is met by a real aggregate; `MilestoneObservation` forbids fabricating a pending observation, and `PerformanceClaim` / `PerformanceClaimPolicy` keep observations distinct from causal conclusions (causal needs an established same-tenant baseline and an adequate caller-supplied sample, and a low-sample movement can be recorded as an interpretation), so Phase 5's milestone-distinctness, missing-baseline and low-sample examples are met; verified by `tests/unit/execution/test_performance_baseline.py`. DONE 2026-10-02 (Ralph cycle 33): pure Governance `PipelineProgress` reports verified progress as the count of approved stage gates derived from the durable `GateLedger` plus caller-supplied verified post-launch milestones, reports activity separately, revokes a gate when a later non-passing decision supersedes it, and rejects negative counts or approved gates exceeding total gates, so SPEC.md section 4's "Display progress as approved gates and verified post launch milestones, never as tasks checked off" is met by a real value; verified by `tests/unit/governance/test_pipeline_progress.py`. DONE 2026-10-03 (Ralph cycle 87): built the Execution `PerformanceBaselinePackage` bridge projecting the reviewed stage 10 baseline onto the twelve canonical kinds. DONE 2026-10-03 (Ralph cycle 88): wired the stage 10 "Performance Baseline Established" `GateDecision` end to end (`StageTenGateAssembler`, `StageTenGateRecorder`, `RecordStageTenGateCommand`, `RecordStageTenGateHandler`), so all eleven gates of the canonical 0-10 template now have a write path; verified by `tests/unit/engagement/test_record_stage_ten_gate.py` (22 tests). Command center intervention ranking is DONE 2026-10-03 (Ralph cycle 90): built the pure Operations `Intervention` card and `InterventionRankingPolicy` ranking blocked critical path, overdue approvals, failed live journeys and nearing commitments with explainable surfacing, dismissal with rationale and deduplication (SPEC.md section 7); verified by `tests/unit/operations/test_intervention_ranking.py` (18 tests). The notification/quiet-hours policy is DONE 2026-10-03 (Ralph cycle 91); verified by `tests/unit/operations/test_notification_policy.py` (22 tests). The improvement loop is DONE 2026-10-03 (Ralph cycle 92): built the Measurement `ImprovementProposal`, `ImprovementApproval`, `ImprovementOutcome` and the approval-gated policies so an optimization stays a proposal until its named owner approves it and is then measured as two observations grounded on an established same-tenant baseline, keeping the movement distinct from a causal conclusion (SPEC.md section 4; Phase 5 "one improvement is approved and measured"; canon files 23 and 24); verified by `tests/unit/measurement/test_improvement_loop.py` (26 tests). The metric registry is DONE 2026-10-03 (Ralph cycle 93): built the Measurement `MetricDefinition`, `MetricUnit`, `MetricDirection`, `MetricFunnelStep`, `MeasurementWindow`, `MeasurementBasis`, `MeasurementRecord` and `MetricBaselinePolicy` so a stage 10 observation pins a typed, versioned, tenant-scoped metric over an explicit window with a placeholder-or-observed basis, value, source and sample, a placeholder cannot establish a baseline and an undersized observed sample is refused (SPEC.md sections 3 and 4; Phase 5 "metric registry"; canon files 23 and 24 inform the metric set); verified by `tests/unit/measurement/test_metric_registry.py` (24 tests); DONE 2026-10-03 (Ralph cycle 95): grounded the improvement loop on that registry -- `ImprovementProposal.metric` and `ImprovementOutcome.metric` are required same-tenant `MetricDefinition`s whose name the subject must match, and the measurement policy refuses an outcome measuring a different metric identity or version (SPEC.md section 3; canon files 23 and 24); verified by the `ImprovementMetricGroundingTests` in `tests/unit/measurement/test_improvement_loop.py` (10 tests), so a stage 10 optimization cannot be proposed or measured against a free-text metric; the next ready item is grounding the outcome's before/after on registered `MeasurementRecord`s.]
11. Complete operational security, backup, GitOps and acceptance drills.

## Risks and decisions

Major risks: fork internals may differ from the prior description; upstream license may limit use; latent cross tenant leakage; AI output may be mistaken for approval; home cluster may lack durable storage or reliable ingress; connector side effects may duplicate on retries; migrating live workflows may strand approval gates. Mitigations are respectively inventory, license review, isolation tests, explicit human authority, restore drills, idempotency keys, and version pinned workflow definitions.

Decisions requiring a named owner: fork URL and license, Kubernetes distribution and capacity, identity provider, database and storage operator, backup target, external access path, model provider data handling, client approval roles, pilot acceptance metrics, 3F launch scope, and the remaining two agent charters. Record these as unresolved until verified. Any work requiring these decisions may proceed to a reviewable proposal and tests, but may not assume authorization from missing information.
