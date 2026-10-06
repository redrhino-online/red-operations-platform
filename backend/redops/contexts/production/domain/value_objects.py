"""Value objects for the Production bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.method.domain.entities import SignatureSolution
from redops.contexts.production.domain.errors import (
    AuthorityAmplifierTenantBoundaryError,
    AuthorityVideoKitDependencyError,
    AuthorityVideoKitFormatError,
    AuthorityVideoKitObservationError,
    AuthorityVideoKitTenantBoundaryError,
    InvalidAuthorityAmplifierError,
    InvalidAuthorityAmplifierPackageError,
    InvalidAuthorityVideoKitError,
)

if TYPE_CHECKING:
    from redops.contexts.production.domain.entities import AuthorityAmplifier


class BuildState(Enum):
    """Lifecycle states of a BuildObject (SPEC.md section 3).

    A build moves from Identified through source, development and review to
    Approved, Production Ready, Deployed, Measuring and Optimizing. Superseded
    and Archived are terminal; an active build is any state that is neither.
    """

    IDENTIFIED = "identified"
    SOURCE_REQUIRED = "source_required"
    READY = "ready"
    IN_DEVELOPMENT = "in_development"
    INTERNAL_REVIEW = "internal_review"
    CLIENT_REVIEW = "client_review"
    CHANGES_REQUIRED = "changes_requested"
    APPROVED = "approved"
    PRODUCTION_READY = "production_ready"
    DEPLOYED = "deployed"
    MEASURING = "measuring"
    OPTIMIZING = "optimizing"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_BUILD_STATES


_TERMINAL_BUILD_STATES = frozenset({BuildState.SUPERSEDED, BuildState.ARCHIVED})


@dataclass(frozen=True)
class BuildTransition:
    """One recorded BuildObject state change (SPEC.md section 4).

    Records the actor, reason, timestamp, old and new state, and correlation ID
    so a build's history can be reconstructed and audited.
    """

    actor: str
    reason: str
    occurred_at: date
    old_state: BuildState
    new_state: BuildState
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise ValueError("build transition actor is required")
        if not self.reason or not self.reason.strip():
            raise ValueError("build transition reason is required")
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("build transition correlation id is required")


class AuthorityAmplifierState(Enum):
    """Readiness of the stage 7 Authority Amplifier (SPEC.md sections 3 and 4).

    Stage 7 has two distinct approvals: the script (with its supported claims)
    before visual or video production, then final creative acceptance. A DRAFT
    amplifier only becomes SCRIPT_APPROVED on script approval and APPROVED on
    creative approval; an upstream change returns it to REVIEW_REQUIRED.
    """

    DRAFT = "draft"
    SCRIPT_APPROVED = "script_approved"
    APPROVED = "approved"
    REVIEW_REQUIRED = "review_required"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_AMPLIFIER_STATES


_TERMINAL_AMPLIFIER_STATES = frozenset(
    {AuthorityAmplifierState.SUPERSEDED, AuthorityAmplifierState.ARCHIVED}
)


class ScriptSectionKind(Enum):
    """The canonical Authority Amplifier script order (SPEC.md section 4).

    Stage 7 requires the approved script in Promise, Proof, Problems, Steps,
    Context, Action order.
    """

    PROMISE = "promise"
    PROOF = "proof"
    PROBLEMS = "problems"
    STEPS = "steps"
    CONTEXT = "context"
    ACTION = "action"


SCRIPT_SECTION_ORDER: tuple[ScriptSectionKind, ...] = (
    ScriptSectionKind.PROMISE,
    ScriptSectionKind.PROOF,
    ScriptSectionKind.PROBLEMS,
    ScriptSectionKind.STEPS,
    ScriptSectionKind.CONTEXT,
    ScriptSectionKind.ACTION,
)


@dataclass(frozen=True)
class ScriptSection:
    """One section of the stage 7 script in its canonical order.

    A section is frozen and reject-only, so a blank section cannot be
    represented as part of an approved script.
    """

    kind: ScriptSectionKind
    content: str

    def __post_init__(self) -> None:
        if not self.content or not self.content.strip():
            raise InvalidAuthorityAmplifierError(
                f"script section {self.kind.value!r} content is required"
            )


@dataclass(frozen=True)
class AmplifierApproval:
    """One version-scoped approval of the stage 7 amplifier.

    The same record type carries both distinct stage 7 approvals; the entity
    stores them in separate fields (script vs creative) so script approval alone
    never constitutes final acceptance. Approval names the actor, intended use
    and date, and the approver identity remains a governance decision.
    """

    approved_by: str
    intended_use: str
    approved_on: date

    def __post_init__(self) -> None:
        if not self.approved_by or not self.approved_by.strip():
            raise InvalidAuthorityAmplifierError("amplifier approver is required")
        if not self.intended_use or not self.intended_use.strip():
            raise InvalidAuthorityAmplifierError(
                "amplifier approval intended use is required"
            )


@dataclass(frozen=True)
class VisualProductionPackage:
    """The stage 7 visual and video assets produced after script approval.

    SPEC.md section 4, stage 7 "Produce": the required asset package includes the
    storyboard, brand treatment, presentation, speaker notes, recording, edited
    and hosted video and player assets. The package is frozen and reject-only, so
    a missing artifact cannot be represented as a completed stage 7 deliverable.
    """

    storyboard: str
    brand_treatment: str
    presentation: str
    speaker_notes: str
    recording: str
    edited_video: str
    hosted_video: str
    player_assets: str

    def __post_init__(self) -> None:
        for label, value in (
            ("storyboard", self.storyboard),
            ("brand treatment", self.brand_treatment),
            ("presentation", self.presentation),
            ("speaker notes", self.speaker_notes),
            ("recording", self.recording),
            ("edited video", self.edited_video),
            ("hosted video", self.hosted_video),
            ("player assets", self.player_assets),
        ):
            if not value or not value.strip():
                raise InvalidAuthorityAmplifierError(
                    f"visual production package {label} is required"
                )


CANONICAL_AMPLIFIER_KINDS: tuple[str, ...] = (
    "authority-amplifier-script",
    "aa-storyboard",
    "brand-treatment",
    "aa-presentation",
    "aa-speaker-notes",
    "aa-recording",
    "aa-edited-video",
    "aa-hosted-video",
    "aa-player-assets",
)


@dataclass(frozen=True)
class AuthorityAmplifierPackage:
    """The reviewed stage 7 amplifier, projected to the nine canonical gate kinds.

    SPEC.md section 4, stage 7 "Produce" and its "Authority Amplifier Approved"
    checkpoint: a stage is complete only when its required assets exist, pass the
    checkpoint and receive approval for downstream use, and a passing gate pins
    the exact evidence. The required asset package is the approved script in
    Promise, Proof, Problems, Steps, Context, Action order, plus the storyboard,
    brand treatment, presentation, speaker notes, recording, edited and hosted
    video and player assets. The Production context reviews that as one rich
    ``AuthorityAmplifier`` (the six script sections and the eight visual assets
    belong to the same amplifier, grounded on the approved stage 6 message and the
    approved method's supported claims); this package is the bridge to the
    governance gate, which pins one exact ``StageAssetVersion`` per canonical kind.

    The canon (SPEC.md section 12.3: stage 7 uses canon files 13-18 and 28)
    requires a six-step script delivered in a fixed order, a branded slide
    presentation carrying that script, and a recorded, edited and uploaded video
    in the standard HD slide size. ``AuthorityAmplifier`` already enforces the
    canonical script order and its dependency on the approved stage 6 message at
    construction, so each canonical kind is projected from the single reviewed
    amplifier at one positive integer version.

    Unlike the stage 1 through 6 reviewed values, an ``AuthorityAmplifier`` only
    owns its visual assets after the script is approved and ``produce_visuals``
    attaches a complete ``VisualProductionPackage``. This package therefore
    refuses an amplifier with no visual package, so eight video kinds cannot be
    pinned as this client's evidence without an asset that actually produced them
    (SPEC.md section 4). It also refuses a blank identity, a versionless amplifier
    or a cross-tenant amplifier rather than silently pinning inexact or foreign
    evidence (SPEC.md sections 3 and 4).
    """

    package_id: str
    tenant_id: str
    amplifier: "AuthorityAmplifier"
    amplifier_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("authority amplifier package id", self.package_id),
            ("authority amplifier package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidAuthorityAmplifierPackageError(f"{label} is required")
        if self.amplifier.tenant_id != self.tenant_id:
            raise AuthorityAmplifierTenantBoundaryError(
                f"stage 7 amplifier {self.amplifier.amplifier_id!r} belongs to "
                f"tenant {self.amplifier.tenant_id!r}, not package tenant "
                f"{self.tenant_id!r}"
            )
        if not isinstance(self.amplifier_version, int) or self.amplifier_version < 1:
            raise InvalidAuthorityAmplifierPackageError(
                "the authority amplifier version must be a positive integer so the "
                "stage 7 gate can pin the reviewed asset at an exact version"
            )
        if self.amplifier.visuals is None:
            raise InvalidAuthorityAmplifierPackageError(
                f"stage 7 amplifier {self.amplifier.amplifier_id!r} has no visual "
                "production package, so its storyboard, presentation, recording, "
                "video and player kinds cannot be pinned as exact evidence"
            )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 7 amplifier projects onto."""
        return frozenset(CANONICAL_AMPLIFIER_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 7 kinds not covered by the projected amplifier."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_AMPLIFIER_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 7 amplifier onto exact governance evidence.

        Every canonical kind belongs to the same reviewed ``AuthorityAmplifier``,
        so each is pinned to that amplifier's identity at its exact version.
        Governance still pins each projection for the workspace tenant, so a
        cross-client amplifier is refused rather than silently authorized (SPEC.md
        sections 3, 4 and 11).
        """
        return tuple(
            StageAssetVersion(
                asset_id=self.amplifier.amplifier_id,
                tenant_id=self.tenant_id,
                kind=kind,
                version=self.amplifier_version,
            )
            for kind in CANONICAL_AMPLIFIER_KINDS
        )


AUTHORITY_VIDEO_CANON_REFERENCE = "13-18; High Ticket Funnels 05, 06, 08"

FLAGSHIP_VIDEO_MIN_MINUTES = 8
FLAGSHIP_VIDEO_MAX_MINUTES = 20
AUTHORITY_STEP_VIDEO_COUNT = 9


class AuthorityVideoKind(Enum):
    """The two video kinds of the canon's 10-pack (canon files 13-18).

    The canon builds one flagship authority video and nine short step videos, one
    per signature-solution step. RED types both so a kit cannot represent a step
    video as the flagship or vice versa.
    """

    FLAGSHIP = "flagship"
    STEP = "step"


@dataclass(frozen=True)
class AuthorityStepVideo:
    """One short step video cut from the flagship script (canon files 13-18).

    The canon cuts the same six-block script into nine short step videos, one per
    signature-solution step. A step video is frozen and reject-only, so a blank
    identity, a blank step name, a blank action or a non-positive duration cannot
    be represented as part of the pack.
    """

    video_id: str
    tenant_id: str
    step_name: str
    title: str
    duration_minutes: int
    action: str

    def __post_init__(self) -> None:
        for label, value in (
            ("authority step video id", self.video_id),
            ("authority step video tenant id", self.tenant_id),
            ("authority step video step name", self.step_name),
            ("authority step video title", self.title),
            ("authority step video action", self.action),
        ):
            if not value or not value.strip():
                raise InvalidAuthorityVideoKitError(f"{label} is required")
        if not isinstance(self.duration_minutes, int) or isinstance(
            self.duration_minutes, bool
        ):
            raise InvalidAuthorityVideoKitError(
                "an authority step video duration must be a whole number of minutes"
            )
        if self.duration_minutes < 1:
            raise InvalidAuthorityVideoKitError(
                f"authority step video {self.video_id!r} must run at least one minute"
            )


@dataclass(frozen=True)
class AuthorityVideoKit:
    """The canon's authority-video 10-pack, built from the stage 7 amplifier.

    SPEC.md section 12.5 records the authority-video kit as a canon gap and the
    implementation plan's canon gap backlog item G2 names this pure-domain
    ``AuthorityVideoKit`` as its bounded slice, an asset inside stage 7, not a new
    stage or required gate kind. The canon (files 13-18; High Ticket Funnels 05,
    06, 08) builds one flagship authority video of 8 to 20 minutes from the
    six-block script (Promise, Proof, Problems, Steps, Context, Action) and cuts
    the same script into nine short step videos, one per signature-solution step.
    The kit extends the stage 7 ``AuthorityAmplifier``: it is grounded on a
    same-tenant amplifier that has produced its video (the canon gate checks the
    script before the slides are made), reuses that amplifier's six-block script,
    and names the nine steps of a same-tenant stage 4 ``SignatureSolution``. It is
    frozen and reject-only, so a blank identity, an untyped or foreign amplifier
    or solution, an amplifier with no produced video, a flagship outside 8 to 20
    minutes, a pack that is not exactly nine step videos, a step video whose step
    the solution does not name, a repeated step, a cross-tenant step video or a
    step video longer than the flagship cannot be represented as the prescribed
    pack.

    The kit is a plan, not a gate kind and not an authorization to publish or
    spend (SPEC.md sections 4 and 9). It is never an observed result; the watch
    time, opt-in rate or booked calls it later produces are separate observations
    (SPEC.md section 3).
    """

    kit_id: str
    tenant_id: str
    owner: str
    amplifier: "AuthorityAmplifier"
    solution: SignatureSolution
    flagship_title: str
    flagship_duration_minutes: int
    flagship_action: str
    step_videos: tuple[AuthorityStepVideo, ...]

    def __post_init__(self) -> None:
        from redops.contexts.production.domain.entities import AuthorityAmplifier

        for label, value in (
            ("authority video kit id", self.kit_id),
            ("authority video kit tenant id", self.tenant_id),
            ("authority video kit owner", self.owner),
            ("authority video flagship title", self.flagship_title),
            ("authority video flagship action", self.flagship_action),
        ):
            if not value or not value.strip():
                raise InvalidAuthorityVideoKitError(f"{label} is required")
        if not isinstance(self.amplifier, AuthorityAmplifier):
            raise AuthorityVideoKitDependencyError(
                "an authority video kit must extend a typed stage 7 Authority "
                "Amplifier, never be built from scratch"
            )
        if self.amplifier.tenant_id != self.tenant_id:
            raise AuthorityVideoKitTenantBoundaryError(
                f"authority video kit {self.kit_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Authority Amplifier "
                f"{self.amplifier.amplifier_id!r} belongs to tenant "
                f"{self.amplifier.tenant_id!r}"
            )
        if not isinstance(self.solution, SignatureSolution):
            raise AuthorityVideoKitDependencyError(
                "an authority video kit must name the typed stage 4 Signature "
                "Solution its nine step videos follow"
            )
        if self.solution.tenant_id != self.tenant_id:
            raise AuthorityVideoKitTenantBoundaryError(
                f"authority video kit {self.kit_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Signature Solution "
                f"{self.solution.solution_id!r} belongs to tenant "
                f"{self.solution.tenant_id!r}"
            )
        if self.amplifier.visuals is None:
            raise AuthorityVideoKitDependencyError(
                f"authority video kit {self.kit_id!r} extends amplifier "
                f"{self.amplifier.amplifier_id!r}, which has not produced its "
                "video; the canon checks the script before the slides and cuts "
                "the nine step videos from the produced video (canon file 13)"
            )
        if not isinstance(self.flagship_duration_minutes, int) or isinstance(
            self.flagship_duration_minutes, bool
        ):
            raise InvalidAuthorityVideoKitError(
                "an authority video flagship duration must be a whole number of "
                "minutes"
            )
        if not (
            FLAGSHIP_VIDEO_MIN_MINUTES
            <= self.flagship_duration_minutes
            <= FLAGSHIP_VIDEO_MAX_MINUTES
        ):
            raise AuthorityVideoKitFormatError(
                f"authority video kit {self.kit_id!r} runs "
                f"{self.flagship_duration_minutes} minutes; the canon keeps the "
                "flagship video to 8 to 20 minutes (canon file 13)"
            )
        videos = tuple(self.step_videos)
        for video in videos:
            if not isinstance(video, AuthorityStepVideo):
                raise InvalidAuthorityVideoKitError(
                    "an authority video kit step video must be a typed step video"
                )
            if video.tenant_id != self.tenant_id:
                raise AuthorityVideoKitTenantBoundaryError(
                    f"authority video kit {self.kit_id!r} belongs to tenant "
                    f"{self.tenant_id!r}, but step video {video.video_id!r} "
                    f"belongs to tenant {video.tenant_id!r}"
                )
        if len(videos) != AUTHORITY_STEP_VIDEO_COUNT:
            raise AuthorityVideoKitFormatError(
                f"authority video kit {self.kit_id!r} carries {len(videos)} step "
                f"videos; the canon cuts the script into exactly "
                f"{AUTHORITY_STEP_VIDEO_COUNT} step videos, one per signature "
                "solution step (canon file 13)"
            )
        step_names = {step.name for step in self.solution.steps}
        for video in videos:
            if video.step_name not in step_names:
                raise AuthorityVideoKitDependencyError(
                    f"authority video kit {self.kit_id!r} carries step video "
                    f"{video.video_id!r} for step {video.step_name!r}, which the "
                    f"Signature Solution {self.solution.solution_id!r} does not "
                    "name; a step video is one step of the signature solution, "
                    "never a new one (canon file 13)"
                )
        named = [video.step_name for video in videos]
        if len(set(named)) != len(named):
            raise AuthorityVideoKitFormatError(
                f"authority video kit {self.kit_id!r} repeats a signature "
                "solution step; the canon gives each step exactly one video "
                "(canon file 13)"
            )
        for video in videos:
            if video.duration_minutes > self.flagship_duration_minutes:
                raise AuthorityVideoKitFormatError(
                    f"authority video kit {self.kit_id!r} step video "
                    f"{video.video_id!r} runs {video.duration_minutes} minutes, "
                    "longer than its flagship video; a step video is a short cut "
                    "of the flagship (canon file 13)"
                )

    @property
    def script(self) -> tuple[ScriptSection, ...]:
        """The six-block script the pack is cut from, reused from the amplifier."""
        return self.amplifier.script

    @property
    def is_plan(self) -> bool:
        """An authority video kit is a plan, not activity or an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent an authority video kit as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The kit
        describes the videos that will be produced, while any measured watch time,
        opt-in rate or booked calls are separate observations, so a kit is never
        an observation.
        """
        raise AuthorityVideoKitObservationError(
            f"authority video kit {claim_id!r} is a pack to produce, not an "
            "observed result, and cannot be recorded as an observation"
        )
