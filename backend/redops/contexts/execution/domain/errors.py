"""Named domain errors for the Execution bounded context (pure domain)."""

from __future__ import annotations


class ExecutionError(Exception):
    """Base class for execution domain rule violations."""


class InvalidFunnelError(ExecutionError, ValueError):
    """A FunnelIntegration or its value objects violate an invariant."""


class FunnelDependencyError(ExecutionError):
    """A funnel is not grounded on an approved stage 7 dependency."""


class FunnelReadinessError(ExecutionError):
    """A complete funnel store was offered a funnel that has not passed its checkpoint.

    SPEC.md sections 3 and 4 pin the exact approved asset versions and intended
    use at a passing gate, so the durable stage 8 store only holds a funnel that
    passed "Funnel Complete". A draft funnel cannot be stored, because a later
    gate would then resolve an uncompleted funnel as if it were approved.
    """


class FunnelVersionConflictError(ExecutionError):
    """A same-id funnel was re-stated with different content.

    SPEC.md section 4 keeps a previous approved version historically
    identifiable: an approved funnel is immutable, so a later stage gate must
    resolve the exact stored stage 8 funnel rather than overwrite it with a
    re-stated request body.
    """


class FunnelVersionTenantBoundaryError(ExecutionError):
    """A funnel store was used without a client scope.

    SPEC.md sections 3 and 9 make a funnel a client resource that must carry its
    tenant on every command and query, so storing or resolving one without a
    client would either leak across clients or create an orphaned record.
    """


class FunnelIncompleteError(ExecutionError):
    """The prospect path does not satisfy the "Funnel Complete" checkpoint."""


class InvalidFunnelIntegrationPackageError(ExecutionError, ValueError):
    """A stage 8 reviewed asset package was built without identity, version or completion.

    SPEC.md sections 3 and 4: a passing stage 8 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 8 ``FunnelIntegration`` is
    projected onto the thirteen canonical asset kinds with a positive integer
    version. A package that leaves its identity or the funnel version unspecified
    cannot be represented as exact gate evidence. The same error is raised when
    the funnel has not passed "Funnel Complete", because its thirteen kinds would
    then be pinned without a completed funnel to own them (a missing asset
    prevents gate completion and a waiver never makes an absent asset appear
    present).
    """


class FunnelIntegrationPackageTenantBoundaryError(ExecutionError):
    """A stage 8 reviewed asset package mixed in a funnel from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``FunnelIntegration`` projected onto a workspace's stage 8 gate package must
    belong to that workspace's tenant. A cross-tenant stage 8 funnel cannot be
    pinned as this client's gate evidence.
    """


class LaunchQAError(ExecutionError):
    """Base class for stage 9 launch QA rule violations."""


class InvalidLaunchQAError(LaunchQAError, ValueError):
    """A LaunchQA or its value objects violate an invariant."""


class LaunchQADependencyError(LaunchQAError):
    """A launch QA is not grounded on a completed stage 8 funnel."""


class LaunchQAIncompleteError(LaunchQAError):
    """Checks do not satisfy the "Launch Approved" checkpoint."""


class LaunchQAAuthorityError(LaunchQAError):
    """Traffic was not authorized by the designated human authority."""


class LaunchQAReadinessError(LaunchQAError):
    """A ready-for-traffic store was offered a QA that has not passed its checkpoint.

    SPEC.md sections 3 and 4 pin the exact approved asset versions and intended
    use at a passing gate, so the durable stage 9 store only holds a QA that
    passed "Launch Approved". A draft QA cannot be stored, because the stage 10
    gate would then resolve an unauthorized QA as if traffic had been authorized.
    """


class LaunchQAVersionConflictError(LaunchQAError):
    """A same-id launch QA was re-stated with different content.

    SPEC.md section 4 keeps a previous approved version historically
    identifiable: an authorized QA is immutable, so the stage 10 gate must
    resolve the exact stored stage 9 QA rather than overwrite it with a re-stated
    request body.
    """


class LaunchQAVersionTenantBoundaryError(LaunchQAError):
    """A launch QA store was used without a client scope.

    SPEC.md sections 3 and 9 make a launch QA a client resource that must carry
    its tenant on every command and query, so storing or resolving one without a
    client would either leak across clients or create an orphaned record.
    """


class InvalidLaunchQAPackageError(LaunchQAError, ValueError):
    """A stage 9 reviewed asset package was built without identity, version or readiness.

    SPEC.md sections 3 and 4: a passing stage 9 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 9 ``LaunchQA`` is projected onto
    the seventeen canonical asset kinds with a positive integer version. A package
    that leaves its identity or the QA version unspecified cannot be represented as
    exact gate evidence. The same error is raised when the QA has not passed
    "Launch Approved", because its seventeen kinds would then be pinned without an
    authorization to begin traffic to own them (a missing asset prevents gate
    completion and a waiver never makes an absent asset appear present).
    """


class ComplianceError(ExecutionError):
    """Base class for stage 9 launch compliance and consent rule violations."""


class InvalidComplianceError(ComplianceError, ValueError):
    """A CompliancePackage, asset or waiver value object violates an invariant."""


class MissingComplianceAssetError(ComplianceError):
    """A launch-blocking compliance asset is absent and not validly waived.

    SPEC.md section 4: consent and the launch compliance assets are required
    "where applicable", and a missing required asset prevents gate completion.
    A waiver never makes an absent asset appear present, so an uncovered missing
    asset refuses the "Launch Approved" traffic authorization rather than being
    silently treated as present.
    """


class ExpiredComplianceWaiverError(ComplianceError):
    """A compliance waiver covering an absent asset has expired.

    SPEC.md section 4: a waiver is a scoped human decision with a reason, risk
    owner and expiry or review trigger, and "a failed or expired prerequisite
    blocks dependent authorization until resolved". An expired waiver therefore
    stops covering its asset and blocks launch even though a waiver was once
    recorded.
    """


class ComplianceTenantBoundaryError(ComplianceError):
    """A compliance package mixed in an asset or QA from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so a
    compliance asset and the QA that pins it must belong to the same tenant. A
    cross-tenant compliance asset cannot be represented as this client's launch
    evidence.
    """


class LaunchQAPackageTenantBoundaryError(LaunchQAError):
    """A stage 9 reviewed asset package mixed in launch QA from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``LaunchQA`` projected onto a workspace's stage 9 gate package must belong to
    that workspace's tenant. A cross-tenant stage 9 QA cannot be pinned as this
    client's gate evidence.
    """


class PerformanceBaselineError(ExecutionError):
    """Base class for stage 10 performance baseline rule violations."""


class InvalidPerformanceBaselineError(PerformanceBaselineError, ValueError):
    """A PerformanceBaseline or its value objects violate an invariant."""


class PerformanceBaselineDependencyError(PerformanceBaselineError):
    """A baseline is not grounded on a ready-for-traffic stage 9 launch QA."""


class PerformanceBaselineIncompleteError(PerformanceBaselineError):
    """Observations do not satisfy "Performance Baseline Established"."""


class PerformanceBaselinePrecedenceError(PerformanceBaselineError):
    """A baseline was established before the evidence it reports existed.

    SPEC.md section 4, stage 10: "Performance Baseline Established" reports
    first qualified traffic and the later lead, appointment and sale milestones
    after the stage 9 authority authorized traffic. A baseline of metrics
    accumulates only after the campaign has run (canon files 23 and 24: "you need
    a baseline of metrics", "don't touch anything for 10 days"), so the
    establishment date must not precede the stage 9 traffic authorization date
    or any milestone the baseline records as observed. Otherwise a baseline could
    claim establishment before the traffic it reports was authorized and
    observed.
    """


class MilestoneObservationPrecedenceError(PerformanceBaselineError):
    """A stage 10 milestone was observed before traffic was authorized.

    SPEC.md section 4, stage 10: first qualified traffic and the later lead,
    appointment and sale milestones are the traffic the stage 9 authority
    authorized. Canon files 23 and 24 ("you need a baseline of metrics", "don't
    touch anything for 10 days") treat the baseline as accumulating only after
    the campaign has run, so an observed ``MilestoneObservation.observed_on``
    must not precede ``qa.authorization.authorized_on``. Otherwise a baseline
    could report a milestone observed before the authority that permitted
    traffic existed.
    """


class MilestoneOrderError(PerformanceBaselineError):
    """A later stage 10 milestone was observed before an earlier one.

    SPEC.md section 4, stage 10: "first qualified traffic and subsequent lead,
    appointment and sale are distinct observed milestones", and canon files 22 and
    23 track the funnel as an ordered value chain (leads, booked sessions, shown
    sessions, customers). A lead cannot be observed after the appointment it
    produces, and an appointment cannot follow the sale. Otherwise a baseline
    could report a sale before any lead and still pass the checkpoint.
    """


class PerformanceClaimError(PerformanceBaselineError):
    """Base class for observation-versus-causal claim rule violations."""


class InvalidPerformanceClaimError(PerformanceClaimError, ValueError):
    """A PerformanceClaim value object violates an invariant."""


class PerformanceClaimSupportError(PerformanceClaimError):
    """A causal claim lacks an established baseline or an adequate sample."""


class InvalidPerformanceBaselinePackageError(
    PerformanceBaselineError, ValueError
):
    """A stage 10 reviewed asset package lacks identity, version or establishment.

    SPEC.md sections 3 and 4: a passing stage 10 gate pins the exact evidence and
    intended downstream use, so the reviewed stage 10 ``PerformanceBaseline`` is
    projected onto the twelve canonical asset kinds with a positive integer
    version. A package that leaves its identity or the baseline version unspecified
    cannot be represented as exact gate evidence. The same error is raised when the
    baseline has not passed "Performance Baseline Established", because its twelve
    kinds would then be pinned without an observed first qualified traffic
    milestone to own them (a missing asset prevents gate completion and a waiver
    never makes an absent asset appear present).
    """


class PerformanceBaselinePackageTenantBoundaryError(PerformanceBaselineError):
    """A stage 10 reviewed asset package mixed in a baseline from another client.

    SPEC.md section 3: every child resource belongs to exactly one client, so the
    ``PerformanceBaseline`` projected onto a workspace's stage 10 gate package must
    belong to that workspace's tenant. A cross-tenant stage 10 baseline cannot be
    pinned as this client's gate evidence.
    """


class SwimlanesError(ExecutionError):
    """Base class for canon Swimlanes channel model rule violations."""


class InvalidSwimlanesError(SwimlanesError, ValueError):
    """A SwimlanesMove or SwimlanesPlan violates an invariant.

    SPEC.md section 12.5 records the canon's Swimlanes channel model -- messages,
    ads, human outreach, offline and direct mail, content (canon files 13, 14, 33
    and 34) -- as a cross-cutting canon gap over stages 8 to 10. The canon's five
    swimlanes are the modalities that "gently move" a stalled prospect "to the
    next step" (canon file 13), so a move names its channel, the step the prospect
    is stuck on, the next step it drives them to, the vehicle it uses and the one
    action it presents. A plan binds a named owner and at least one typed move.
    A blank identity, a missing or untyped field, a move that does not change the
    prospect's step, an empty or untyped move set, or a duplicate move identity
    cannot be represented as a recovery plan.
    """


class SwimlanesTenantBoundaryError(SwimlanesError):
    """A Swimlanes plan mixed in a funnel or move from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    swimlanes plan belongs to the tenant of the stage 8 funnel it recovers for, so
    a plan cannot cross a tenant boundary and a move cannot come from another
    client.
    """


class SwimlanesDependencyError(SwimlanesError):
    """A Swimlanes plan was not grounded on a typed stage 8 funnel.

    SPEC.md section 12.5 places the Swimlanes channel model cross-cutting over
    stages 8 to 10, and the plan recovers prospects that stall in the integrated
    stage 8 funnel. A plan must therefore be grounded on a typed, same-tenant
    ``FunnelIntegration`` before it can plan recovery moves for it.
    """


class EnrollmentError(ExecutionError):
    """Base class for canon enrollment and sales call rule violations."""


class InvalidEnrollmentError(EnrollmentError, ValueError):
    """An enrollment call step, homework, qualification, payment or plan violates an invariant.

    SPEC.md section 12.5 records the canon's enrollment and sales call -- the pre-call
    homework qualifier, the medical-style frame/examine/prescribe/prognosis call and
    the acceptance and rejection ("red velvet rope") criteria -- as a canon gap
    between stages 8 and 10, shaped by canon files 00, 06, 13, 14, 21 and 24. The
    canon names a four-stage medical call ("there's analysis, there's kind of an
    examination, a prescription, and a prognosis", canon file 00), a pre-call
    homework that draws "a piece of my signature solution" and schedules "within 72
    hours. No more than that" (canon file 21), the red velvet rope of who is
    accepted and rejected (canon file 06) and a live payment captured over card or
    PayPal (canon file 21). A blank identity, a missing or untyped field, a
    duplicate question or criterion, a call window outside the canon bound, a
    non-positive deposit, a payment not captured live, or a plan that does not
    carry exactly the canon stages in order cannot be represented as an enrollment
    plan.
    """


class EnrollmentDependencyError(EnrollmentError):
    """An enrollment plan was not grounded on a typed, complete stage 8 funnel.

    SPEC.md section 12.5 places the enrollment and sales call between stages 8 and
    10, after the same-tenant stage 8 ``FunnelIntegration`` has passed "Funnel
    Complete". A plan must therefore be grounded on a typed ``FunnelIntegration``,
    and ``EnrollmentReadinessPolicy`` refuses to run the enrollment call before the
    funnel it converts prospects through is complete.
    """


class EnrollmentTenantBoundaryError(EnrollmentError):
    """An enrollment plan mixed in a funnel from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. An
    enrollment plan belongs to the tenant of the stage 8 funnel it converts for, so
    a plan cannot cross a tenant boundary.
    """


class EnrollmentObservationError(EnrollmentError):
    """An enrollment plan was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The plan
    describes the call that will run and the payment terms that will be offered,
    while any enrolled prospect or collected payment stays a separate observed or
    authorized record, so a plan is never an observation.
    """


class SwimlaneCoverageError(SwimlanesError):
    """A Swimlanes plan depends on too few channels to recover stalled prospects.

    The canon warns "you can't just rely on email" and "you can't be single source
    dependent" (canon file 34), and SPEC.md section 12.5 requires recovering
    stalled prospects "across all channels, not only digital ads". A plan that
    does not use all five canon channels is missing the reach the model exists to
    provide, so the coverage policy refuses it rather than presenting a partial
    plan as complete.
    """


class SwimlanesObservationError(SwimlanesError):
    """A Swimlanes plan was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The plan
    describes the recovery moves that will run, while any measured movement stays
    a separate observation, so a plan is never an observation.
    """


class ClientProcessError(ExecutionError):
    """Base class for the client-authored enrollment process rule violations."""


class InvalidClientProcessError(ClientProcessError, ValueError):
    """A client process value object or the process violates an invariant.

    SPEC.md section 12.7 makes the client-authored enrollment process a versioned
    artifact whose required shape is fixed by the supplied canon: the six part
    enrollment process in order (frame, discover problems, prescription,
    application, invitation, plus the objection crusher), the five pass-or-fail
    checkpoints (intent, commitment, value, confidence, desire) each with the
    client's own question, the acceptance and rejection criteria, the common
    objection answers, the chosen strategy-session model, the price floor, the
    pre-call homework, the booking window and the no-show rules. A blank identity
    or owner, a missing or untyped field, a duplicate question, checkpoint,
    criterion or objection, a price floor that is not positive, or a process that
    does not carry exactly the canon parts and checkpoints in order cannot be
    represented as a client process.
    """


class ClientProcessDependencyError(ClientProcessError):
    """A client process was not grounded on a typed, complete upstream asset.

    SPEC.md section 12.7 grounds the client's process on the client's own
    approved stage 2 currency, stage 3 model, stage 4 Signature Solution and stage
    5 product roadmap (canon files 35-49). A process must therefore be grounded on
    typed same-tenant values, and ``ClientProcessReadinessPolicy`` refuses to treat
    a process as ready when its stage 5 program does not yet deliver every stage 4
    method step, because a client cannot enroll prospects into a program that does
    not deliver the client's own method.
    """


class ClientProcessTenantBoundaryError(ClientProcessError):
    """A client process mixed in a currency, model, method or program from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. The
    client process belongs to the tenant of the stage 2 currency, stage 3 model,
    stage 4 method and stage 5 program it is grounded on, so it cannot cross a
    tenant boundary.
    """


class ClientProcessObservationError(ClientProcessError):
    """A client process was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The process
    describes the enrollment conversation the client will run and the terms it
    will offer, while any enrolled prospect, collected payment or measured
    movement stays a separate observed or authorized record, so the process is
    never an observation.
    """


class JourneyReleaseError(ExecutionError):
    """Base class for the SPEC.md section 3 journey release rule violations."""


class InvalidJourneyReleaseError(JourneyReleaseError, ValueError):
    """A JourneyRelease value violates an invariant.

    SPEC.md section 3 names ``JourneyRelease`` (assets, routing, configuration
    digest, rollback ref) as a core aggregate, and SPEC.md section 4 makes
    launch require "integration checks, customer path dry run, consent where
    applicable, named operator, rollback". A blank identity, routing,
    configuration digest or rollback reference, an empty released asset set, or
    an asset package that does not pin exactly one exact version per kind cannot
    be represented as a journey release.
    """


class JourneyReleaseDependencyError(JourneyReleaseError):
    """A journey release was not grounded on a typed stage 9 launch QA.

    SPEC.md sections 3 and 4 ground a launch on the reviewed stage 9 launch QA
    ("Launch Approved: all critical path checks pass, exceptions have owners, and
    the designated human authorizes traffic"), so a release must be grounded on
    a typed ``LaunchQA`` rather than an untyped readiness claim.
    """


class JourneyReleaseReadinessError(JourneyReleaseError):
    """A journey release was offered a QA that is not signed ready and authorized.

    SPEC.md section 3 states the ``JourneyRelease`` invariant: "launch needs
    signed readiness and authorized release". A stage 9 launch QA that has not
    reached ``READY_FOR_TRAFFIC``, or that carries no ``TrafficAuthorization``,
    cannot authorize a launch, so no journey release can be built from it.
    """


class JourneyReleaseAuthorityError(JourneyReleaseError):
    """A journey release pinned an authorization by a non-designated actor.

    SPEC.md section 4: approval is version specific and "an agent cannot confer
    human approval upon itself", and stage 9 requires "the designated human
    authorizes traffic". A release cannot pin a traffic authorization whose actor
    is not the QA's designated authority, even if the QA's state claims readiness.
    """


class JourneyReleaseTenantBoundaryError(JourneyReleaseError):
    """A journey release mixed in a QA or asset from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    release belongs to the tenant of the launch QA and of every released asset it
    pins, so it cannot cross a tenant boundary.
    """


class JourneyReleaseVersionConflictError(JourneyReleaseError):
    """A same-id journey release was re-stated with different content.

    SPEC.md section 4 keeps a previous deployed release historically
    identifiable: an authorized release is immutable, so a later release must be
    a new identity rather than overwrite the stored one with a re-stated body.
    """


class JourneyReleaseVersionTenantBoundaryError(JourneyReleaseError):
    """A journey release store was used without a client scope.

    SPEC.md sections 3 and 9 make a journey release a client resource that must
    carry its tenant on every command and query, so storing or resolving one
    without a client would either leak across clients or create an orphaned
    record.
    """


class ConnectorError(ExecutionError):
    """Base class for outbound connector rule violations."""


class InvalidConnectorEffectError(ConnectorError, ValueError):
    """A ConnectorEffect or ExternalOperation violates an invariant.

    SPEC.md section 6 calls connectors "outbound adapters with explicit scopes
    and replay safe operations", and SPEC.md section 7 requires a request
    identity and idempotency key on every mutation where a retry matters. An
    effect must therefore name its client, idempotency key, connector, target and
    exact content digest, and a recorded operation must name its external
    reference. A blank field cannot be represented as a replay-safe effect.
    """


class ConnectorIdempotencyConflictError(ConnectorError):
    """An idempotency key was reused with different content.

    SPEC.md section 11 requires "duplicate delivery creates one external
    operation". A repeat of the *same* effect must resolve to the one recorded
    operation, but a reused key that carries different content is a different
    operation that would silently be suppressed, so the connector refuses it
    rather than sending a second external effect under a key already spent.
    """


class ConnectorTenantBoundaryError(ConnectorError):
    """A connector effect or operation was used without a client scope.

    SPEC.md sections 3 and 9 make an outbound operation a client resource that
    must carry its tenant on every command and query, so delivering or resolving
    one without a client would either leak across clients or create an orphaned
    operation.
    """
