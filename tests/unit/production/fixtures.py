"""Shared pure-domain fixtures for Production tests.

These build a valid stage 7 `AuthorityAmplifier` grounded on the approved stage
6 message, an approved method and directly sourced knowledge claims, so tests
that exercise script and creative approval do not restate the same content in
every file. They are test data only and carry no behavior.
"""

from __future__ import annotations

from datetime import date

from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)
from redops.contexts.production.domain.entities import AuthorityAmplifier
from redops.contexts.production.domain.value_objects import (
    SCRIPT_SECTION_ORDER,
    ScriptSection,
    VisualProductionPackage,
)

from ..commercial.fixtures import approved_method, campaign_message

TENANT = "client-3f"
TODAY = date(2026, 10, 2)
USE = "3f pilot campaign"


def known_claim(claim_id: str = "claim-1", tenant_id: str = TENANT) -> Claim:
    return Claim(
        claim_id=claim_id,
        tenant_id=tenant_id,
        statement=f"{claim_id} statement",
        provenance=ProvenanceClass.KNOWN,
        citations=frozenset(
            {SourceCitation("source-1", "checksum-1", "page 1")}
        ),
        confidence_note="directly observed",
    )


def script(replacements=None) -> tuple[ScriptSection, ...]:
    values = {
        kind: f"{kind.value} content" for kind in SCRIPT_SECTION_ORDER
    }
    values.update(replacements or {})
    return tuple(
        ScriptSection(kind, values[kind]) for kind in SCRIPT_SECTION_ORDER
    )


def approved_message():
    return campaign_message().approve([approved_method()])


def visual_package(**overrides) -> VisualProductionPackage:
    values = {
        "storyboard": "asset://aa/storyboard",
        "brand_treatment": "asset://aa/brand",
        "presentation": "asset://aa/slides",
        "speaker_notes": "asset://aa/notes",
        "recording": "asset://aa/recording",
        "edited_video": "asset://aa/edited",
        "hosted_video": "asset://aa/hosted",
        "player_assets": "asset://aa/player",
    }
    values.update(overrides)
    return VisualProductionPackage(**values)


def authority_amplifier(message=None, **overrides) -> AuthorityAmplifier:
    values = {
        "amplifier_id": "amplifier-3f",
        "tenant_id": TENANT,
        "message": approved_message() if message is None else message,
        "owner": "production-manager",
        "script": script(),
        "proof_claim_ids": frozenset({"claim-1"}),
    }
    values.update(overrides)
    return AuthorityAmplifier(**values)


def script_approved_amplifier(**overrides) -> AuthorityAmplifier:
    amplifier = authority_amplifier(**overrides)
    return amplifier.approve_script(
        approved_by="production-manager",
        intended_use=USE,
        on=TODAY,
        approved_methods=(approved_method(),),
        claims=(known_claim(),),
    )


def approved_amplifier(**overrides) -> AuthorityAmplifier:
    """A stage 7 amplifier that received both approvals at the gate boundary.

    Script approval (supported proof) comes before visual production, then the
    separate final creative acceptance, so this is exactly the asset the stage 8
    to 10 gates resolve from the store (SPEC.md section 4, stage 7).
    """
    return (
        script_approved_amplifier(**overrides)
        .produce_visuals(package=visual_package())
        .approve_creative(
            approved_by="client-authority",
            intended_use=USE,
            on=TODAY,
        )
    )
