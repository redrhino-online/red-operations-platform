"""Map the Method ``MethodVersion`` aggregate to and from a durable payload.

SPEC.md section 6 keeps mapping in the infrastructure layer: the domain must not
know about JSONB or table columns. The PostgreSQL adapter stores an approved
``MethodVersion`` as a JSONB payload plus a few indexed columns, and rebuilds the
aggregate on load by going through ``MethodVersion.__post_init__``. Serialising
every authority-bearing field -- the exact semantic version, the ``MethodApproval``
that pins the version and intended use, and the pinned stage 2 primary currency,
stage 3 diagnostic model and stage 4 Signature Solution -- is what lets a reloaded
method re-validate rather than trust what storage claims (SPEC.md sections 3 and
4: approval pins an exact version and intended use, and a previous approved
version stays historically identifiable). A round trip that silently dropped the
approval or a pinned dependency would turn a draft or a stale version back into
an approved method on reload.

Canon: not applicable. This is a persistence mapper for a method aggregate, not a
method artifact, so no reference-model file informs its shape.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from redops.contexts.method.domain.entities import (
    DiagnosticModel,
    MethodVersion,
    SignatureSolution,
)
from redops.contexts.method.domain.value_objects import (
    MethodApproval,
    PrimaryCurrency,
    ProfitPyramidLevel,
    SemanticVersion,
    SignatureStep,
    TransformationPhase,
)


def _text_list(values: Any) -> list[str]:
    return [str(value) for value in values]


def _primary_currency_to_payload(currency: PrimaryCurrency) -> dict[str, Any]:
    return {
        "tenant_id": currency.tenant_id,
        "currency": currency.currency,
        "audience": currency.audience,
        "current_measure": currency.current_measure,
        "desired_measure": currency.desired_measure,
        "mechanism": currency.mechanism,
    }


def _primary_currency_from_payload(
    payload: Mapping[str, Any],
) -> PrimaryCurrency:
    return PrimaryCurrency(
        tenant_id=str(payload["tenant_id"]),
        currency=str(payload["currency"]),
        audience=str(payload["audience"]),
        current_measure=str(payload["current_measure"]),
        desired_measure=str(payload["desired_measure"]),
        mechanism=str(payload["mechanism"]),
    )


def _level_to_payload(level: ProfitPyramidLevel) -> dict[str, Any]:
    return {
        "level_id": level.level_id,
        "tenant_id": level.tenant_id,
        "name": level.name,
        "observable_measures": list(level.observable_measures),
        "symptoms": list(level.symptoms),
        "behaviors": list(level.behaviors),
        "problems": list(level.problems),
    }


def _level_from_payload(payload: Mapping[str, Any]) -> ProfitPyramidLevel:
    return ProfitPyramidLevel(
        level_id=str(payload["level_id"]),
        tenant_id=str(payload["tenant_id"]),
        name=str(payload["name"]),
        observable_measures=tuple(
            str(entry) for entry in payload["observable_measures"]
        ),
        symptoms=tuple(str(entry) for entry in payload["symptoms"]),
        behaviors=tuple(str(entry) for entry in payload["behaviors"]),
        problems=tuple(str(entry) for entry in payload["problems"]),
    )


def _model_to_payload(model: DiagnosticModel) -> dict[str, Any]:
    return {
        "model_id": model.model_id,
        "tenant_id": model.tenant_id,
        "name": model.name,
        "levels": [_level_to_payload(level) for level in model.levels],
        "progression": model.progression,
        "qualification_logic": model.qualification_logic,
        "visual": model.visual,
        "explanatory_copy": model.explanatory_copy,
    }


def _model_from_payload(payload: Mapping[str, Any]) -> DiagnosticModel:
    return DiagnosticModel(
        model_id=str(payload["model_id"]),
        tenant_id=str(payload["tenant_id"]),
        name=str(payload["name"]),
        levels=tuple(
            _level_from_payload(level) for level in payload["levels"]
        ),
        progression=str(payload["progression"]),
        qualification_logic=str(payload["qualification_logic"]),
        visual=str(payload["visual"]),
        explanatory_copy=str(payload["explanatory_copy"]),
    )


def _step_to_payload(step: SignatureStep) -> dict[str, Any]:
    return {
        "step_id": step.step_id,
        "tenant_id": step.tenant_id,
        "name": step.name,
        "starting_state": step.starting_state,
        "final_state": step.final_state,
        "inputs": list(step.inputs),
        "actions": list(step.actions),
        "outputs": list(step.outputs),
    }


def _step_from_payload(payload: Mapping[str, Any]) -> SignatureStep:
    return SignatureStep(
        step_id=str(payload["step_id"]),
        tenant_id=str(payload["tenant_id"]),
        name=str(payload["name"]),
        starting_state=str(payload["starting_state"]),
        final_state=str(payload["final_state"]),
        inputs=tuple(str(entry) for entry in payload["inputs"]),
        actions=tuple(str(entry) for entry in payload["actions"]),
        outputs=tuple(str(entry) for entry in payload["outputs"]),
    )


def _phase_to_payload(phase: TransformationPhase) -> dict[str, Any]:
    return {
        "phase_id": phase.phase_id,
        "tenant_id": phase.tenant_id,
        "name": phase.name,
        "steps": [_step_to_payload(step) for step in phase.steps],
    }


def _phase_from_payload(payload: Mapping[str, Any]) -> TransformationPhase:
    return TransformationPhase(
        phase_id=str(payload["phase_id"]),
        tenant_id=str(payload["tenant_id"]),
        name=str(payload["name"]),
        steps=tuple(
            _step_from_payload(step) for step in payload["steps"]
        ),
    )


def _solution_to_payload(solution: SignatureSolution) -> dict[str, Any]:
    return {
        "solution_id": solution.solution_id,
        "tenant_id": solution.tenant_id,
        "transformation_map": solution.transformation_map,
        "process_inventory": list(solution.process_inventory),
        "phases": [_phase_to_payload(phase) for phase in solution.phases],
        "starting_state": solution.starting_state,
        "final_state": solution.final_state,
        "narrative": solution.narrative,
        "visual": solution.visual,
    }


def _solution_from_payload(payload: Mapping[str, Any]) -> SignatureSolution:
    return SignatureSolution(
        solution_id=str(payload["solution_id"]),
        tenant_id=str(payload["tenant_id"]),
        transformation_map=str(payload["transformation_map"]),
        process_inventory=tuple(
            str(entry) for entry in payload["process_inventory"]
        ),
        phases=tuple(
            _phase_from_payload(phase) for phase in payload["phases"]
        ),
        starting_state=str(payload["starting_state"]),
        final_state=str(payload["final_state"]),
        narrative=str(payload["narrative"]),
        visual=str(payload["visual"]),
    )


def signature_solution_to_payload(solution: SignatureSolution) -> dict[str, Any]:
    """Public wrapper for a Signature Solution payload, reused by other contexts.

    The stage 5 ``DeliverySpecification`` in the Commercial context is grounded
    on the locked stage 4 Signature Solution, so the offer mapper reuses this
    exact serialisation rather than inventing a second shape that could drift
    (SPEC.md section 3: every tenant resource pins an exact approved version).
    """

    return _solution_to_payload(solution)


def signature_solution_from_payload(
    payload: Mapping[str, Any],
) -> SignatureSolution:
    """Rebuild a Signature Solution through its aggregate invariants."""

    return _solution_from_payload(payload)


def _approval_to_payload(approval: MethodApproval) -> dict[str, Any]:
    return {
        "version": str(approval.version),
        "intended_use": approval.intended_use,
        "approved_by": approval.approved_by,
        "approved_on": approval.approved_on.isoformat(),
    }


def _approval_from_payload(payload: Mapping[str, Any]) -> MethodApproval:
    return MethodApproval(
        version=SemanticVersion.parse(str(payload["version"])),
        intended_use=str(payload["intended_use"]),
        approved_by=str(payload["approved_by"]),
        approved_on=date.fromisoformat(str(payload["approved_on"])),
    )


def method_to_payload(method: MethodVersion) -> dict[str, Any]:
    """Serialise an approved method into the JSONB payload the table stores.

    ``claims`` is emitted in a stable sorted order so the payload is
    deterministic where the domain treats it as a set; stages and the
    transformation phases and steps keep their declared order, which carries
    meaning. An optional dependency is emitted as ``None`` rather than dropped,
    so a reload cannot confuse an absent dependency with a malformed one.
    """
    return {
        "method_id": method.method_id,
        "tenant_id": method.tenant_id,
        "parent_method": method.parent_method,
        "semantic_version": str(method.semantic_version),
        "stages": list(method.stages),
        "currency": method.currency,
        "claims": sorted(method.claims),
        "approval": (
            _approval_to_payload(method.approval)
            if method.approval is not None
            else None
        ),
        "primary_currency": (
            _primary_currency_to_payload(method.primary_currency)
            if method.primary_currency is not None
            else None
        ),
        "diagnostic_model": (
            _model_to_payload(method.diagnostic_model)
            if method.diagnostic_model is not None
            else None
        ),
        "signature_solution": (
            _solution_to_payload(method.signature_solution)
            if method.signature_solution is not None
            else None
        ),
    }


def method_from_payload(payload: Mapping[str, Any]) -> MethodVersion:
    """Rebuild a method from a stored payload for re-validation.

    Construction re-runs the aggregate invariants. A payload that storage cannot
    legally hold (an unknown version, a missing approval field, a pinned
    dependency from another tenant) raises here rather than being read back as an
    approved method.
    """
    approval = payload.get("approval")
    primary_currency = payload.get("primary_currency")
    diagnostic_model = payload.get("diagnostic_model")
    signature_solution = payload.get("signature_solution")
    return MethodVersion(
        method_id=str(payload["method_id"]),
        tenant_id=str(payload["tenant_id"]),
        parent_method=str(payload["parent_method"]),
        semantic_version=SemanticVersion.parse(
            str(payload["semantic_version"])
        ),
        stages=tuple(str(stage) for stage in payload["stages"]),
        currency=str(payload["currency"]),
        claims=frozenset(str(claim) for claim in payload.get("claims", ())),
        approval=(
            _approval_from_payload(approval) if approval is not None else None
        ),
        primary_currency=(
            _primary_currency_from_payload(primary_currency)
            if primary_currency is not None
            else None
        ),
        diagnostic_model=(
            _model_from_payload(diagnostic_model)
            if diagnostic_model is not None
            else None
        ),
        signature_solution=(
            _solution_from_payload(signature_solution)
            if signature_solution is not None
            else None
        ),
    )
