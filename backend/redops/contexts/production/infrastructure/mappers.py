"""Map the Production ``AuthorityAmplifier`` aggregate to and from a durable payload.

SPEC.md section 6 keeps mapping in the infrastructure layer: the domain must not
know about JSONB or table columns. The PostgreSQL adapter stores an approved
stage 7 ``AuthorityAmplifier`` as a JSONB payload plus a few indexed columns, and
rebuilds the aggregate on load by going through ``AuthorityAmplifier.__post_init__``
and the approval methods. Serialising every authority-bearing field -- the
grounding stage 6 ``CampaignMessage``, the canonical six-section script in order,
the proof claim ids, the complete ``VisualProductionPackage`` and both distinct
approvals (script before visual, then creative) -- is what lets a reloaded
amplifier re-validate rather than trust what storage claims (SPEC.md sections 3
and 4: a passing gate pins the exact approved asset versions and intended use,
and a previous approved version stays historically identifiable). A round trip
that silently dropped the visual package or one of the two approvals would turn a
stale or unapproved amplifier back into an approved one on reload.

The nested stage 6 message is serialised with the Commercial context's own mapper
helper so the two contexts cannot drift on the shape of that shared asset.

Canon: not applicable. This is a persistence mapper for a production aggregate,
not a method artifact, so no reference-model file informs its shape.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from redops.contexts.commercial.infrastructure.mappers import (
    campaign_message_from_payload,
    campaign_message_to_payload,
)
from redops.contexts.production.domain.entities import AuthorityAmplifier
from redops.contexts.production.domain.value_objects import (
    AmplifierApproval,
    AuthorityAmplifierState,
    ScriptSection,
    ScriptSectionKind,
    VisualProductionPackage,
)


def _approval_to_payload(approval: AmplifierApproval | None) -> dict[str, Any] | None:
    if approval is None:
        return None
    return {
        "approved_by": approval.approved_by,
        "intended_use": approval.intended_use,
        "approved_on": approval.approved_on.isoformat(),
    }


def _approval_from_payload(
    payload: Mapping[str, Any] | None,
) -> AmplifierApproval | None:
    if payload is None:
        return None
    return AmplifierApproval(
        approved_by=str(payload["approved_by"]),
        intended_use=str(payload["intended_use"]),
        approved_on=date.fromisoformat(str(payload["approved_on"])),
    )


def _script_to_payload(
    script: tuple[ScriptSection, ...],
) -> list[dict[str, Any]]:
    return [
        {"kind": section.kind.value, "content": section.content}
        for section in script
    ]


def _script_from_payload(
    payload: list[Mapping[str, Any]],
) -> tuple[ScriptSection, ...]:
    return tuple(
        ScriptSection(
            kind=ScriptSectionKind(str(entry["kind"])),
            content=str(entry["content"]),
        )
        for entry in payload
    )


def _visuals_to_payload(
    visuals: VisualProductionPackage | None,
) -> dict[str, Any] | None:
    if visuals is None:
        return None
    return {
        "storyboard": visuals.storyboard,
        "brand_treatment": visuals.brand_treatment,
        "presentation": visuals.presentation,
        "speaker_notes": visuals.speaker_notes,
        "recording": visuals.recording,
        "edited_video": visuals.edited_video,
        "hosted_video": visuals.hosted_video,
        "player_assets": visuals.player_assets,
    }


def _visuals_from_payload(
    payload: Mapping[str, Any] | None,
) -> VisualProductionPackage | None:
    if payload is None:
        return None
    return VisualProductionPackage(
        storyboard=str(payload["storyboard"]),
        brand_treatment=str(payload["brand_treatment"]),
        presentation=str(payload["presentation"]),
        speaker_notes=str(payload["speaker_notes"]),
        recording=str(payload["recording"]),
        edited_video=str(payload["edited_video"]),
        hosted_video=str(payload["hosted_video"]),
        player_assets=str(payload["player_assets"]),
    )


def authority_amplifier_to_payload(amplifier: AuthorityAmplifier) -> dict[str, Any]:
    """Serialise an approved amplifier into the JSONB payload the table stores.

    The grounding message is emitted through ``campaign_message_to_payload`` so
    the amplifier cannot drift from the message shape, and the script keeps its
    canonical order. The optional visual package and each approval are emitted as
    ``None`` rather than dropped, so a reload cannot confuse an absent asset with
    a malformed one.
    """

    return {
        "amplifier_id": amplifier.amplifier_id,
        "tenant_id": amplifier.tenant_id,
        "message": campaign_message_to_payload(amplifier.message),
        "owner": amplifier.owner,
        "script": _script_to_payload(amplifier.script),
        "proof_claim_ids": sorted(amplifier.proof_claim_ids),
        "visuals": _visuals_to_payload(amplifier.visuals),
        "script_approval": _approval_to_payload(amplifier.script_approval),
        "creative_approval": _approval_to_payload(amplifier.creative_approval),
        "state": amplifier.state.value,
        "review_reason": amplifier.review_reason,
    }


def authority_amplifier_from_payload(
    payload: Mapping[str, Any],
) -> AuthorityAmplifier:
    """Rebuild an amplifier from a stored payload for re-validation.

    Construction re-runs the aggregate invariants, so a payload that storage
    cannot legally hold (a blank identity, a missing script section, a grounding
    message from another tenant) raises here rather than being read back as an
    approved amplifier.
    """

    return AuthorityAmplifier(
        amplifier_id=str(payload["amplifier_id"]),
        tenant_id=str(payload["tenant_id"]),
        message=campaign_message_from_payload(payload["message"]),
        owner=str(payload["owner"]),
        script=_script_from_payload(payload["script"]),
        proof_claim_ids=frozenset(
            str(entry) for entry in payload["proof_claim_ids"]
        ),
        visuals=_visuals_from_payload(payload.get("visuals")),
        script_approval=_approval_from_payload(payload.get("script_approval")),
        creative_approval=_approval_from_payload(
            payload.get("creative_approval")
        ),
        state=AuthorityAmplifierState(str(payload["state"])),
        review_reason=payload.get("review_reason"),
    )
