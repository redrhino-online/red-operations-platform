"""Value objects for the Production bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.production.domain.errors import (
    AuthorityAmplifierTenantBoundaryError,
    InvalidAuthorityAmplifierError,
    InvalidAuthorityAmplifierPackageError,
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
