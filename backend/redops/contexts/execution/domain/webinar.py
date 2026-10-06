"""The canon winning-webinar kit (pure domain), shaped by canon 32.

SPEC.md section 12.5 records the webinar kit as a canon gap: a six-phase run of
show, slides, email and retargeting, the scaled path of enrollment. The
implementation plan's canon gap backlog item G3 names this pure-domain
``WebinarKit`` as its bounded slice, a stage 6/8/10 asset and the scaled
enrollment path, not a new stage or required gate kind. The canon supplies the
substance:

- Canon file 32 and the Winning Webinar series fix the six-phase run of show
  (frame, teach, shift, sell, show, close) of about 60 minutes, three teach blocks
  that match the three phases of the signature solution, one offer, the page set
  (sign up, train, webinar, replay, order), the 5P email sequence, the 3 to 5 day
  closing sequence, the replay to everyone and retargeting by where each group
  stopped.
- Winning Webinar 13 fixes the ten-and-ten rule: automate a webinar only after ten
  live runs at 10% or better, and never present an automated webinar as live.
- Synthesized ``ops/playbooks/webinar.md``,
  ``ops/checklists/webinar-run-of-show.md`` and ``ops/sops/webinar-build.md`` fix
  the six phases, the about-60-minute clock, the simple path first, and the
  closing sequence.

The canon says "six phases" while the synthesized playbook names five sections
(frame, teach, shift, sell, show); RED resolves the count by including the closing
sequence as the sixth phase, which the playbook and checklist both require. That
reconciliation is recorded here rather than silently diverging.

Canon text is treated as data (SPEC.md section 12.2): only structure, terminology
and intent are extracted, never copied. The kit is a plan, not an observation
(SPEC.md section 3); it does not authorize sending, spend, publishing or any
client commitment (SPEC.md sections 4 and 9), which stay human decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from redops.contexts.execution.domain.errors import (
    InvalidWebinarError,
    WebinarAutomationError,
    WebinarDependencyError,
    WebinarFormatError,
    WebinarObservationError,
    WebinarTenantBoundaryError,
)
from redops.contexts.method.domain.entities import SignatureSolution

WEBINAR_CANON_REFERENCE = "32; Winning Webinar 01-13"

# The canon runs the webinar for "about 60 minutes" (canon file 32; synthesized
# playbook and checklist).
WEBINAR_TARGET_MINUTES = 60
WEBINAR_MIN_MINUTES = 50
WEBINAR_MAX_MINUTES = 70

# The canon's three teach blocks match the three phases of the signature solution.
WEBINAR_TEACH_BLOCK_COUNT = 3

# Winning Webinar 13: automate only after ten live runs at 10% or better.
WEBINAR_AUTOMATION_LIVE_RUNS = 10
WEBINAR_AUTOMATION_CONVERSION_PERCENT = 10

# The canon runs the closing sequence for 3 to 5 days.
WEBINAR_CLOSING_MIN_DAYS = 3
WEBINAR_CLOSING_MAX_DAYS = 5


class WebinarPhase(Enum):
    """The canon's six-phase run of show (canon file 32).

    The canon names six phases; the synthesized playbook enumerates frame, teach,
    shift, sell and show, and the closing sequence the playbook and checklist both
    require is counted here as the sixth phase.
    """

    FRAME = "frame"
    TEACH = "teach"
    SHIFT = "shift"
    SELL = "sell"
    SHOW = "show"
    CLOSE = "close"


WEBINAR_PHASE_ORDER: tuple[WebinarPhase, ...] = (
    WebinarPhase.FRAME,
    WebinarPhase.TEACH,
    WebinarPhase.SHIFT,
    WebinarPhase.SELL,
    WebinarPhase.SHOW,
    WebinarPhase.CLOSE,
)


class WebinarPage(Enum):
    """The canon's five-page set (canon file 32)."""

    SIGN_UP = "sign-up"
    TRAIN = "train"
    WEBINAR = "webinar"
    REPLAY = "replay"
    ORDER = "order"


WEBINAR_PAGE_ORDER: tuple[WebinarPage, ...] = (
    WebinarPage.SIGN_UP,
    WebinarPage.TRAIN,
    WebinarPage.WEBINAR,
    WebinarPage.REPLAY,
    WebinarPage.ORDER,
)


class WebinarEmailKind(Enum):
    """The canon's 5P email types (canon file 32; synthesized playbook)."""

    PROBLEM = "problem"
    PROMISE = "promise"
    PROOF = "proof"
    PING = "ping"
    PROMOTION = "promotion"


WEBINAR_EMAIL_ORDER: tuple[WebinarEmailKind, ...] = (
    WebinarEmailKind.PROBLEM,
    WebinarEmailKind.PROMISE,
    WebinarEmailKind.PROOF,
    WebinarEmailKind.PING,
    WebinarEmailKind.PROMOTION,
)


class WebinarMode(Enum):
    """Whether the webinar runs live or automated (Winning Webinar 13)."""

    LIVE = "live"
    AUTOMATED = "automated"


class EnrollmentPath(Enum):
    """The canon's two enrollment paths (canon file 32; synthesized playbook).

    The simple path is a lead magnet to a call; the scaled path is a lead to a
    webinar to a call. The canon builds the simple path first, then adds the
    webinar, so the webinar kit is the scaled path.
    """

    SIMPLE = "simple"
    SCALED = "scaled"


def _require_blank_free(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidWebinarError(f"{label} is required")


def _require_blank_free_unique(label: str, values: Iterable[str]) -> None:
    items = tuple(values)
    if not items:
        raise InvalidWebinarError(f"a webinar requires at least one {label}")
    seen: set[str] = set()
    for value in items:
        if not isinstance(value, str) or not value.strip():
            raise InvalidWebinarError(f"a webinar {label} is required")
        if value in seen:
            raise InvalidWebinarError(f"a webinar repeats {label} {value!r}")
        seen.add(value)


@dataclass(frozen=True)
class WebinarPhaseBlock:
    """One phase of the canon's six-phase run of show (canon file 32).

    The canon keeps the webinar on a fixed clock, so each phase carries its
    purpose and its minutes. A block is frozen and reject-only: a blank purpose, a
    non-positive duration or an untyped phase cannot be represented as part of the
    run of show.
    """

    phase: WebinarPhase
    purpose: str
    minutes: int

    def __post_init__(self) -> None:
        if not isinstance(self.phase, WebinarPhase):
            raise InvalidWebinarError(
                "a webinar phase block must name one of the canon phases"
            )
        _require_blank_free("webinar phase purpose", self.purpose)
        if isinstance(self.minutes, bool) or not isinstance(self.minutes, int):
            raise InvalidWebinarError(
                "a webinar phase duration must be a whole number of minutes"
            )
        if self.minutes <= 0:
            raise InvalidWebinarError(
                "a webinar phase duration must be positive"
            )


@dataclass(frozen=True)
class WebinarTeachBlock:
    """One of the canon's three teach blocks (canon file 32).

    The canon teaches the what, not the how, and each teach block matches one
    phase of the signature solution: a promise of a measurable outcome and the
    obstacles the avatar faces with that phase. A block is frozen and reject-only:
    a blank phase name or promise, or an empty or duplicate obstacle set, cannot be
    represented as a teach block.
    """

    phase_name: str
    promise: str
    obstacles: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_blank_free("webinar teach block phase name", self.phase_name)
        _require_blank_free("webinar teach block promise", self.promise)
        _require_blank_free_unique(
            "teach block obstacle", tuple(self.obstacles)
        )


@dataclass(frozen=True)
class WebinarPageSet:
    """The canon's five-page set (canon file 32).

    The canon builds the pages sign up, train, webinar, replay and order. The set
    is frozen and reject-only: it must carry exactly the canon's five pages once
    each, in order.
    """

    pages: tuple[WebinarPage, ...]

    def __post_init__(self) -> None:
        pages = tuple(self.pages)
        for page in pages:
            if not isinstance(page, WebinarPage):
                raise InvalidWebinarError(
                    "a webinar page must be one of the canon pages"
                )
        if pages != WEBINAR_PAGE_ORDER:
            raise WebinarFormatError(
                "a webinar page set must carry exactly the canon pages sign up, "
                "train, webinar, replay and order, once each, in order (canon "
                "file 32)"
            )


@dataclass(frozen=True)
class WebinarEmail:
    """One email of the canon's 5P sequence (canon file 32).

    The canon sends the email sequence using the 5P types. An email is frozen and
    reject-only: a blank subject or an untyped kind cannot be represented as part
    of the sequence.
    """

    kind: WebinarEmailKind
    subject: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, WebinarEmailKind):
            raise InvalidWebinarError(
                "a webinar email must name one of the canon 5P types"
            )
        _require_blank_free("webinar email subject", self.subject)


@dataclass(frozen=True)
class WebinarEmailSequence:
    """The canon's 5P email sequence (canon file 32).

    The canon sends the email sequence using the 5P types (problem, promise,
    proof, ping, promotion). The sequence is frozen and reject-only: it must carry
    exactly the five 5P types once each, in order.
    """

    emails: tuple[WebinarEmail, ...]

    def __post_init__(self) -> None:
        emails = tuple(self.emails)
        for item in emails:
            if not isinstance(item, WebinarEmail):
                raise InvalidWebinarError(
                    "a webinar email must be a typed email"
                )
        kinds = tuple(item.kind for item in emails)
        if kinds != WEBINAR_EMAIL_ORDER:
            raise WebinarFormatError(
                "a webinar email sequence must carry exactly the canon 5P types "
                "problem, promise, proof, ping and promotion, once each, in order "
                "(canon file 32)"
            )


@dataclass(frozen=True)
class WebinarClosingSequence:
    """The canon's closing sequence (canon file 32).

    The canon runs the closing sequence for 3 to 5 days, and it drives most of the
    sales. The sequence is frozen and reject-only: it must run 3 to 5 days and
    carry at least one duplicate-free closing step.
    """

    days: int
    steps: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.days, bool) or not isinstance(self.days, int):
            raise InvalidWebinarError(
                "a webinar closing sequence must run a whole number of days"
            )
        if not (
            WEBINAR_CLOSING_MIN_DAYS
            <= self.days
            <= WEBINAR_CLOSING_MAX_DAYS
        ):
            raise WebinarFormatError(
                f"a webinar closing sequence runs {self.days} days; the canon "
                "runs it for 3 to 5 days (canon file 32)"
            )
        _require_blank_free_unique("closing step", tuple(self.steps))


@dataclass(frozen=True)
class WebinarAutomation:
    """The canon's ten-and-ten automation gate (Winning Webinar 13).

    The canon automates a webinar only after ten live runs at 10% or better, and
    it never presents an automated webinar as live. The value is frozen and
    reject-only: an automated webinar below the bar, or one presented as live, is
    refused rather than represented as the canon's scaled path.
    """

    mode: WebinarMode
    live_runs: int
    conversion_percent: int
    presented_as_live: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mode, WebinarMode):
            raise InvalidWebinarError(
                "a webinar automation must name the live or automated mode"
            )
        for label, value in (
            ("live runs", self.live_runs),
            ("conversion percent", self.conversion_percent),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise InvalidWebinarError(
                    f"a webinar automation {label} must be a whole number"
                )
            if value < 0:
                raise InvalidWebinarError(
                    f"a webinar automation {label} must not be negative"
                )
        if self.mode is WebinarMode.AUTOMATED:
            if self.presented_as_live:
                raise WebinarAutomationError(
                    "an automated webinar cannot be presented as live; the canon "
                    "says never fake it (Winning Webinar 13)"
                )
            if (
                self.live_runs < WEBINAR_AUTOMATION_LIVE_RUNS
                or self.conversion_percent
                < WEBINAR_AUTOMATION_CONVERSION_PERCENT
            ):
                raise WebinarAutomationError(
                    "a webinar may be automated only after "
                    f"{WEBINAR_AUTOMATION_LIVE_RUNS} live runs at "
                    f"{WEBINAR_AUTOMATION_CONVERSION_PERCENT}% or better; this "
                    f"automation records {self.live_runs} runs at "
                    f"{self.conversion_percent}% (Winning Webinar 13)"
                )

    @property
    def is_automated(self) -> bool:
        """Whether the webinar runs automated rather than live."""
        return self.mode is WebinarMode.AUTOMATED

    @property
    def meets_automation_bar(self) -> bool:
        """Whether the recorded runs clear the canon's ten-and-ten bar."""
        return (
            self.live_runs >= WEBINAR_AUTOMATION_LIVE_RUNS
            and self.conversion_percent
            >= WEBINAR_AUTOMATION_CONVERSION_PERCENT
        )


@dataclass(frozen=True)
class WebinarKit:
    """The canon winning-webinar kit (SPEC.md section 12.5, backlog G3).

    The kit binds a named owner to a same-tenant stage 4 ``SignatureSolution``, the
    chosen enrollment path, the six-phase run of show, the three teach blocks, the
    one offer, the page set, the 5P email sequence, the closing sequence, the
    replay to everyone, the retargeting groups and the automation gate. It is the
    typed form of the scaled enrollment path.

    It is frozen and reject-only, so the canon's shape cannot be bypassed: the path
    must be the scaled path and the simple path must be proven first, the run of
    show must carry exactly the canon's six phases in order on an about-60-minute
    clock, the teach blocks must match the three signature-solution phases in
    order, the offer must be present, the page set and email sequence must carry
    exactly the canon's pages and 5P types in order, the closing sequence must run
    3 to 5 days, the replay must go to everyone, at least one retargeting group is
    required, and an automated webinar must clear the ten-and-ten bar and never be
    presented as live. It is a stage 6/8/10 planning asset, not a required gate
    kind, and it does not authorize sending, spend, publishing or any client
    commitment (SPEC.md sections 4 and 9). It is never an observation (SPEC.md
    section 3).
    """

    kit_id: str
    tenant_id: str
    owner: str
    solution: SignatureSolution
    path: EnrollmentPath
    simple_path_proven: bool
    phases: tuple[WebinarPhaseBlock, ...]
    teach_blocks: tuple[WebinarTeachBlock, ...]
    offer: str
    pages: WebinarPageSet
    emails: WebinarEmailSequence
    closing: WebinarClosingSequence
    replay_to_all: bool
    retargeting_groups: tuple[str, ...]
    automation: WebinarAutomation

    def __post_init__(self) -> None:
        for label, value in (
            ("webinar kit id", self.kit_id),
            ("webinar kit tenant id", self.tenant_id),
            ("webinar kit owner", self.owner),
        ):
            _require_blank_free(label, value)
        self._require_grounding()
        self._require_path()
        self._require_run_of_show()
        self._require_teach_blocks()
        _require_blank_free("webinar offer", self.offer)
        if not isinstance(self.pages, WebinarPageSet):
            raise InvalidWebinarError(
                "a webinar kit requires a typed page set"
            )
        if not isinstance(self.emails, WebinarEmailSequence):
            raise InvalidWebinarError(
                "a webinar kit requires a typed 5P email sequence"
            )
        if not isinstance(self.closing, WebinarClosingSequence):
            raise InvalidWebinarError(
                "a webinar kit requires a typed closing sequence"
            )
        if self.replay_to_all is not True:
            raise WebinarFormatError(
                "the canon sends the replay to everyone, including people who "
                "missed it (canon file 32)"
            )
        _require_blank_free_unique(
            "retargeting group", tuple(self.retargeting_groups)
        )
        if not isinstance(self.automation, WebinarAutomation):
            raise InvalidWebinarError(
                "a webinar kit requires a typed automation gate"
            )

    def _require_grounding(self) -> None:
        if not isinstance(self.solution, SignatureSolution):
            raise WebinarDependencyError(
                "a webinar kit must be grounded on a typed stage 4 Signature "
                "Solution"
            )
        if self.solution.tenant_id != self.tenant_id:
            raise WebinarTenantBoundaryError(
                f"webinar kit {self.kit_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Signature Solution "
                f"{self.solution.solution_id!r} belongs to tenant "
                f"{self.solution.tenant_id!r}"
            )

    def _require_path(self) -> None:
        if not isinstance(self.path, EnrollmentPath):
            raise InvalidWebinarError(
                "a webinar kit must name the chosen enrollment path"
            )
        if self.path is not EnrollmentPath.SCALED:
            raise WebinarFormatError(
                "the webinar kit is the scaled path (a lead to a webinar to a "
                "call); the simple path is a lead magnet to a call (canon file 32)"
            )
        if self.simple_path_proven is not True:
            raise WebinarFormatError(
                "the canon builds the simple path first, then adds the webinar; "
                "the simple path must be proven before the scaled path (canon "
                "file 32)"
            )

    def _require_run_of_show(self) -> None:
        phases = tuple(self.phases)
        for block in phases:
            if not isinstance(block, WebinarPhaseBlock):
                raise InvalidWebinarError(
                    "a webinar phase block must be a typed phase block"
                )
        if tuple(block.phase for block in phases) != WEBINAR_PHASE_ORDER:
            raise WebinarFormatError(
                "a webinar run of show must carry exactly the canon's six phases "
                "frame, teach, shift, sell, show and close, once each, in order "
                "(canon file 32)"
            )
        total = sum(block.minutes for block in phases)
        if not (WEBINAR_MIN_MINUTES <= total <= WEBINAR_MAX_MINUTES):
            raise WebinarFormatError(
                f"a webinar run of show runs {total} minutes; the canon runs it "
                "for about 60 minutes (canon file 32)"
            )

    def _require_teach_blocks(self) -> None:
        blocks = tuple(self.teach_blocks)
        for block in blocks:
            if not isinstance(block, WebinarTeachBlock):
                raise InvalidWebinarError(
                    "a webinar teach block must be a typed teach block"
                )
        solution_phases = tuple(phase.name for phase in self.solution.phases)
        for block in blocks:
            if block.phase_name not in solution_phases:
                raise WebinarDependencyError(
                    f"webinar kit {self.kit_id!r} carries a teach block for phase "
                    f"{block.phase_name!r}, which the Signature Solution "
                    f"{self.solution.solution_id!r} does not name; the three teach "
                    "blocks match the three signature-solution phases (canon "
                    "file 32)"
                )
        if tuple(block.phase_name for block in blocks) != solution_phases:
            raise WebinarFormatError(
                f"webinar kit {self.kit_id!r} must carry exactly "
                f"{WEBINAR_TEACH_BLOCK_COUNT} teach blocks, one per "
                "signature-solution phase, in order (canon file 32)"
            )

    @property
    def canon_reference(self) -> str:
        """The canon file block whose structure shaped this artifact."""
        return WEBINAR_CANON_REFERENCE

    @property
    def phase_kinds(self) -> tuple[WebinarPhase, ...]:
        """The canon phases the run of show carries, in order."""
        return tuple(block.phase for block in self.phases)

    @property
    def total_minutes(self) -> int:
        """The length of the run of show (canon file 32)."""
        return sum(block.minutes for block in self.phases)

    @property
    def feeds_stages(self) -> tuple[int, ...]:
        """The downstream stages the kit feeds (SPEC.md section 12.5)."""
        return (6, 8, 10)

    @property
    def is_plan(self) -> bool:
        """A webinar kit is a plan, not activity or an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a webinar kit as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The kit
        describes the webinar that will run and the terms it will offer, while any
        registration, show, conversion or revenue stays a separate observed or
        authorized record, so a kit is never an observation.
        """
        raise WebinarObservationError(
            f"webinar kit {claim_id!r} is a webinar to run, not an observed "
            "result, and cannot be recorded as an observation"
        )
