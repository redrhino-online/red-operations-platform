"""Adapter that answers whether a stage's RED approval is recorded (K12).

SPEC.md section 14 condition 8 binds each pipeline gate to the RED approval the
stage gate records: a run pauses at the gate and resumes only after that
approval is recorded. The check reads the tenant's durable ``GateLedger``
through the Governance repository port, so the workflow use case never touches
the Governance store directly (SPEC.md section 6) and the answer is the same one
the production view derives from.
"""

from __future__ import annotations

from datetime import date

from redops.contexts.governance.application.ports import GateLedgerRepository
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.workflows.application.ports import StageGateApprovalPort


class StageGateApprovalRepository(StageGateApprovalPort):
    """Answer the gate-approval question from the durable gate ledger."""

    def __init__(self, repository: GateLedgerRepository) -> None:
        self._repository = repository

    def has_passing_decision(self, *, tenant_id: str, stage_number: int) -> bool:
        template = stage_zero_to_ten_template()
        ledger = self._repository.load(template, tenant_id)
        return ledger.has_passing_decision(stage_number, on=date.today())
