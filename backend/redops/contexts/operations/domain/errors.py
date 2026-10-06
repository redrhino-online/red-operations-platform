"""Named domain errors for the Operations bounded context (pure domain)."""

from __future__ import annotations


class OperationsError(Exception):
    """Base class for operations domain rule violations."""


class InvalidInterventionError(OperationsError, ValueError):
    """An intervention card was built without the fields SPEC.md section 7 requires.

    SPEC.md section 7 lists the command center intervention fields as client,
    severity, reason, evidence, owner, next action, due time, state and affected
    builds, and requires the card to show why it was surfaced. A card missing its
    owner, evidence or explanation would present an unexplained intervention with
    no accountable party, so it is refused rather than rendered.
    """


class InterventionDismissalError(OperationsError):
    """An intervention was dismissed without a rationale or after it was closed.

    SPEC.md section 7 allows a card to be dismissed with rationale. A dismissal
    without a rationale would erase why an operator suppressed the card, and a
    card that is already dismissed or resolved is no longer open to dismiss.
    """


class InvalidInterventionQueryError(OperationsError, ValueError):
    """The intervention query was configured in a way its rules forbid.

    The nearing-commitment window must be a positive number of days; a zero or
    negative window would make "nearing" meaningless.
    """


class InvalidInterventionDismissalError(OperationsError, ValueError):
    """A recorded intervention dismissal is missing a field or is malformed.

    SPEC.md section 7 allows a card to be dismissed with rationale and requires
    the card to show who owns it and why it was surfaced. A durable dismissal
    record therefore names the tenant, client, reason and subject of the card it
    suppresses, the operator's rationale and the actor who dismissed it; a record
    missing any of these would suppress an intervention without a traceable
    decision or cross a client boundary.
    """


class InterventionDismissalConflictError(OperationsError):
    """A stored dismissal was re-stated with different content under its key.

    A dismissal is an operator decision and is append only: recording the exact
    same dismissal again is idempotent, but reusing a card's key with a different
    rationale or actor would rewrite the decision history rather than add to it.
    """


class InterventionDismissalTenantBoundaryError(OperationsError):
    """A dismissal was stored or resolved without a client tenant.

    SPEC.md sections 3 and 9 make an intervention a client resource that must
    carry its tenant on every command and query; storing or reading one without a
    client would either leak across clients or create an orphaned decision.
    """


class InvalidQuietHoursError(OperationsError, ValueError):
    """An owner's quiet-hours preference is missing or ambiguous.

    SPEC.md section 7 requires notifications to respect owner quiet hours. A
    preference with no owner cannot be routed, a non-time boundary cannot define
    a window, and one owner with two conflicting preferences cannot have an
    unambiguous schedule. Every case is refused rather than guessed.
    """


class InvalidNotificationError(OperationsError, ValueError):
    """A notification record is missing a required field or is self-contradictory.

    A notification must identify the intervention it carries (client, reason,
    subject) and its owner, and it must be exactly one of delivered or
    suppressed: a delivered notification cannot claim a suppression reason, and a
    suppressed notification must record why it was withheld rather than dropped
    silently (SPEC.md section 7).
    """


class InvalidServiceLineError(OperationsError, ValueError):
    """A service-line artifact was built without the content the canon requires.

    SPEC.md section 12.5 records the canon's service-line artifacts (the kickoff
    checklist, module production standard, session guide, client scorecard and
    case study template) as a canon gap, and the implementation plan's backlog
    item G7 names typed artifacts for them. A service line names its tenant, a
    named owner, the same-tenant stage 5 ``ProductProgram`` it delivers and the
    five artifacts; each artifact carries the fields its canon checklist requires
    (a named delivery lead, goals written as a number and a date, collected
    access, a module goal and one currency, a session goal, idea, example and
    task, the four scorecard dimensions, and a case study's identity and content).
    A blank identity, an empty goal, access, step, dimension or risk set, or an
    untyped part cannot be represented as a service-line artifact.
    """


class ServiceLineTenantBoundaryError(OperationsError):
    """A service line mixed in a program or case study from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    service line belongs to the tenant of the client whose program it delivers,
    so it cannot be grounded on another tenant's program or carry another
    tenant's case study.
    """


class ServiceLineDependencyError(OperationsError):
    """A service line was not grounded on a typed stage 5 program.

    The canon's service line delivers the productized program one module per week
    (``internal/service-ops.md``), so a service line must be grounded on a typed
    same-tenant stage 5 ``ProductProgram`` before it can be the delivery plan.
    """


class ServiceLineFormatError(OperationsError):
    """A service-line artifact broke the canon's service shape.

    The canon's kickoff welcomes the client within one business day and puts the
    first module on or after the start date (synthesized
    ``ops/checklists/kickoff.md``); the module production standard runs its steps
    once each (synthesized ``ops/checklists/module-production.md``); and the
    scorecard watches the four canon dimensions in order (synthesized
    ``ops/checklists/client-scorecard.md``). A late welcome, a first module before
    the start, a repeated step or a missing, repeated or reordered scorecard
    dimension is refused rather than silently accepted.
    """


class ServiceLineGateError(OperationsError):
    """A service-line artifact was confirmed without meeting its canon gate.

    The canon's kickoff is done only when the one-page plan is shared
    (synthesized ``ops/checklists/kickoff.md``), the module production standard is
    done only when the script and slides match, the video is on brand and the
    module is published (synthesized ``ops/checklists/module-production.md``), and
    the scorecard is done only when it is shared with the delivery lead
    (synthesized ``ops/checklists/client-scorecard.md``). Confirming an unmet gate
    is refused, so a checklist cannot claim a completion the canon does not allow.
    """


class ServiceLineObservationError(OperationsError):
    """A service line was asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. A service
    line is the delivery plan and its checklists, while any attendance, progress,
    result or published case study stays a separate observation, so a service
    line is never an observation.
    """


class CaseStudyProofError(OperationsError):
    """A case study claim was made without a real, measured result.

    The canon's case study capture confirms the result is real and measured and
    collects the starting and ending numbers before writing the story
    (synthesized ``ops/checklists/case-study.md`` and
    ``ops/sops/case-study-capture.md``), and SPEC.md section 1 forbids an
    unreviewed performance claim. A claim on an unmeasured result or with missing
    numbers is refused, so the platform never presents an unsourced testimonial.
    """


class CaseStudyAuthorityError(OperationsError):
    """A case study claim was made without written permission or an approved quote.

    The canon's case study capture requires written permission and a client
    approved quote, and says never to publish a story without written permission
    (synthesized ``ops/checklists/case-study.md`` and
    ``ops/sops/case-study-capture.md``). SPEC.md sections 1 and 4 forbid an
    unreviewed testimonial and require client approval. A claim without written
    permission or with an unapproved quote is refused, so the platform never
    presents an unapproved testimonial.
    """


class CaseStudyVersionError(OperationsError):
    """A case study claim was made without a version scope or intended use.

    SPEC.md section 4 scopes client-approved information to a version and
    intended use, and SPEC.md section 3 pins an exact version at approval. A claim
    that does not name the approved version and the intended use is refused, so
    client-approved proof cannot be reused outside the scope it was approved for.
    """
