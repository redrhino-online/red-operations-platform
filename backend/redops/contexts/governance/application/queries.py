"""Application query use cases for the Governance bounded context.

SPEC.md section 6 places use cases between the entry points and the domain: an
API or worker calls a use case, the use case composes domain services, and it
depends on domain types and ports rather than on web, ORM, queue or vendor code.
SPEC.md section 4 requires a production-manager view that answers, for each
client, the current stage, what is present and approved, who is accountable,
which dependency blocks work and what approval is next, and SPEC.md section 4
requires a failed or expired prerequisite to block dependent authorization until
resolved.

``EngagementProductionView.from_ledger`` (pure domain) already derives that view
from a versioned ``StageTemplate`` and a durable ``GateLedger``. It cannot load
its own inputs, because Governance never reads its own store in the domain. This
use case is the application seam that loads the tenant's ledger through the
``GateLedgerRepository`` port and each stage's durable ``StageRun`` through the
``StageRunRepository`` port, then hands them to the domain view. It holds no rule
of its own: it loads, assembles and returns, so gate integrity, accountability
and tenant scoping stay enforced by the domain and the ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from redops.contexts.governance.application.ports import (
    GateLedgerRepository,
    StageRunRepository,
)
from redops.contexts.governance.domain.entities import StageRun
from redops.contexts.governance.domain.value_objects import (
    EngagementProductionView,
    MetricReportingView,
    StageTemplate,
    UmbrellaPlanReportingView,
)


@dataclass(frozen=True)
class EngagementProductionViewQuery:
    """Request the production-manager view for one client engagement.

    The template is supplied by the caller (the canonical
    ``stage_zero_to_ten_template`` for the running platform) because it is
    read-only reference data, not state a store owns. The engagement and tenant
    label the view and scope the loads; the evaluation instant ``on`` fixes the
    dependency and expiry check. Milestone and activity counts and the typed
    observed metric rows are supplied by the caller because the Measurement and
    Operations contexts own them, and the view never infers or fabricates them
    (SPEC.md section 4).
    """

    template: StageTemplate
    engagement: str
    tenant_id: str
    on: date
    verified_post_launch_milestones: int = 0
    activity_entries: int = 0
    metric_reporting: tuple[MetricReportingView, ...] = ()
    umbrella_plan: UmbrellaPlanReportingView | None = None


class GetEngagementProductionViewHandler:
    """Derive the production view from the durable ledger and stage runs.

    The handler loads the tenant's append-only ``GateLedger`` for the query's
    template and tenant, then loads the ``StageRun`` for each stage the template
    defines. A stage with no run is a stage that has not started and is omitted;
    the view reports it as not-started rather than inventing progress. The loaded
    runs and ledger are passed to ``EngagementProductionView.from_ledger``, which
    remains the single place the projection, tenant boundary and dependency rules
    are validated (SPEC.md sections 4 and 6).
    """

    def __init__(
        self,
        *,
        ledger_repository: GateLedgerRepository,
        run_repository: StageRunRepository,
    ) -> None:
        self._ledger_repository = ledger_repository
        self._run_repository = run_repository

    def handle(
        self, query: EngagementProductionViewQuery
    ) -> EngagementProductionView:
        ledger = self._ledger_repository.load(query.template, query.tenant_id)
        runs: list[StageRun] = []
        for definition in query.template.stages:
            run = self._run_repository.load(
                query.template.version,
                query.engagement,
                definition.stage_number,
                query.tenant_id,
            )
            if run is not None:
                runs.append(run)
        return EngagementProductionView.from_ledger(
            ledger,
            engagement=query.engagement,
            tenant_id=query.tenant_id,
            on=query.on,
            verified_post_launch_milestones=query.verified_post_launch_milestones,
            activity_entries=query.activity_entries,
            metric_reporting=query.metric_reporting,
            umbrella_plan=query.umbrella_plan,
            stage_runs=tuple(runs),
        )
