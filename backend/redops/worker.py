"""RED background worker entrypoint (SPEC.md sections 6 and 7; ADR 0005).

``python -m redops.worker`` is the composition consumer of the durable workflow
resume use case. It composes ``ResumeDueRunsHandler`` with the durable
``WorkflowRunStore`` and the connector-backed ``ConnectorStepExecutor``, then
advances the in-flight runs that are due for its configured clients, one client
at a time (SPEC.md section 7: "Persist run state before side effects; resume from
committed steps"; ADR 0005: one scheduler and one worker, gated so a single claim
path exists).

The loop is deliberately thin: every resume goes through the same use case the
API uses, so resumption stays idempotent, a client's scan is tenant scoped, and a
waiting approval is left for its human (SPEC.md sections 9 and 11). A failure on
one client is caught, logged and retried on the next pass rather than killing the
process, because the run was persisted before the side effect and remains
resumable.

Configuration is read from the environment (SPEC.md section 10):

``DATABASE_URL``
    The durable PostgreSQL store. When set, the worker uses the durable
    ``WorkflowRunStore`` and ``ExternalOperationStore``; when unset it uses the
    in-memory reference adapters for local development.
``REDOP_WORKER_TENANTS``
    The comma-separated client roster to scan. Defaults to the pilot client.
``REDOP_CONNECTOR_NAME``
    The connector the step executor delivers through. Defaults to ``redop``.

A durable worker additionally needs a real connector transport so a recorded
external operation is actually sent. The connector inventory is an open
decision (SPEC.md section 11), so with ``DATABASE_URL`` set and no transport
configured the worker refuses to start with ``WorkerConfigurationError`` rather
than record a durable operation it cannot send. The chart's worker Deployment
therefore stays disabled until that transport is configured.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Callable, Mapping
from datetime import date
from uuid import uuid4

from redops.contexts.execution.application.ports import (
    ConnectorPort,
    ConnectorTransport,
)
from redops.contexts.execution.infrastructure.connectors import (
    IdempotentConnector,
    RecordingConnectorTransport,
    external_operation_store_from_env,
)
from redops.workflows.application.handlers import ResumeDueRunsHandler
from redops.workflows.application.ports import (
    WorkflowRunStore,
    WorkflowStepExecutor,
)
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.infrastructure.executors import ConnectorStepExecutor
from redops.workflows.infrastructure.repositories import workflow_run_store_from_env

logger = logging.getLogger("redops.worker")

DEFAULT_TENANT = "3fmindset"
DEFAULT_ACTOR = "worker"
DEFAULT_REASON = "resume due workflow runs"
DEFAULT_CONNECTOR_NAME = "redop"
DEFAULT_TICK_SECONDS = 15.0


class WorkerConfigurationError(RuntimeError):
    """The worker was configured in a way it cannot honestly run.

    A durable worker needs both a durable run store and a connector transport
    that actually sends the recorded external operation (SPEC.md section 6). A
    blank client roster is a misconfiguration, not an instruction to scan every
    client: the store scan is tenant scoped by design (SPEC.md section 9), so the
    worker refuses to guess. Failing fast keeps the worker from running in a mode
    that silently drops work.
    """


def parse_tenant_roster(raw: str | None) -> tuple[str, ...]:
    """Parse ``REDOP_WORKER_TENANTS`` into the clients this worker serves.

    ``None`` selects the pilot client. Any supplied value must be a
    comma-separated list of non-blank, non-repeated client ids; a malformed
    roster is refused rather than partly honored (SPEC.md section 9).
    """

    if raw is None:
        return (DEFAULT_TENANT,)
    tenants = tuple(part.strip() for part in raw.split(","))
    if not tenants or any(not tenant for tenant in tenants):
        raise WorkerConfigurationError(
            "REDOP_WORKER_TENANTS must be a comma-separated list of non-blank "
            "client ids"
        )
    if len(set(tenants)) != len(tenants):
        raise WorkerConfigurationError(
            "REDOP_WORKER_TENANTS must not repeat a client id"
        )
    return tenants


def connector_transport_from_env(
    environ: Mapping[str, str],
) -> ConnectorTransport:
    """Select the connector transport from configuration (SPEC.md section 6).

    Without a ``DATABASE_URL`` the worker runs in reference mode and records
    effects with the process-local ``RecordingConnectorTransport``, matching the
    in-memory stores used in local development. With a ``DATABASE_URL`` the
    output would be durable, so a transport that does not actually send would
    record a false success; there is no configured vendor transport yet (the
    connector inventory is an open decision, SPEC.md section 11), so the worker
    refuses to start instead of pretending.
    """

    if environ.get("DATABASE_URL"):
        raise WorkerConfigurationError(
            "a durable worker requires a configured connector transport; the "
            "connector inventory is an open decision (SPEC.md section 11), so "
            "the worker refuses to record a durable external operation it "
            "cannot actually send"
        )
    return RecordingConnectorTransport()


def _tick_seconds(environ: Mapping[str, str]) -> float:
    """Return the seconds between resume passes, defaulting to a gentle tick."""

    raw = environ.get("REDOP_WORKER_TICK_SECONDS")
    if raw is None or not raw.strip():
        return DEFAULT_TICK_SECONDS
    try:
        seconds = float(raw)
    except ValueError as exc:
        raise WorkerConfigurationError(
            "REDOP_WORKER_TICK_SECONDS must be a number of seconds"
        ) from exc
    if seconds <= 0:
        raise WorkerConfigurationError(
            "REDOP_WORKER_TICK_SECONDS must be greater than zero"
        )
    return seconds


def build_worker(
    *,
    store: WorkflowRunStore,
    executor: WorkflowStepExecutor,
    tenants: tuple[str, ...],
    actor: str = DEFAULT_ACTOR,
    reason: str = DEFAULT_REASON,
    clock: Callable[[], date] = date.today,
) -> "WorkflowWorker":
    """Compose the resume use case with its store and executor (SPEC.md §6).

    This is the single place the worker wires the durable ``WorkflowRunStore``
    to the ``ResumeDueRunsHandler`` and the connector-backed
    ``ConnectorStepExecutor``, so the loop depends only on the composition and
    never on a concrete database or connector.
    """

    return WorkflowWorker(
        handler=ResumeDueRunsHandler(store=store, executor=executor),
        tenants=tenants,
        actor=actor,
        reason=reason,
        clock=clock,
    )


class WorkflowWorker:
    """The durable workflow resume loop (SPEC.md sections 7 and 9).

    Each pass asks the tenant-scoped handler for the runs due for a configured
    client and resumes them. The loop holds no state between passes: a restart
    simply reloads the durable runs and continues from their committed steps.
    """

    def __init__(
        self,
        *,
        handler: ResumeDueRunsHandler,
        tenants: tuple[str, ...],
        actor: str = DEFAULT_ACTOR,
        reason: str = DEFAULT_REASON,
        clock: Callable[[], date] = date.today,
        correlation_id_factory: Callable[[], str] | None = None,
        log: logging.Logger = logger,
    ) -> None:
        roster = tuple(tenants)
        if not roster or any(not tenant or not tenant.strip() for tenant in roster):
            raise WorkerConfigurationError(
                "a workflow worker requires at least one non-blank client tenant"
            )
        self._handler = handler
        self._tenants = roster
        self._actor = actor
        self._reason = reason
        self._clock = clock
        self._correlation_id_factory = (
            correlation_id_factory
            if correlation_id_factory is not None
            else _new_correlation_id
        )
        self._log = log

    @property
    def tenants(self) -> tuple[str, ...]:
        return self._tenants

    def run_once(self, *, on: date | None = None) -> tuple[WorkflowRun, ...]:
        """Resume every due run for every configured client.

        A failure for one client is logged and swallowed so the remaining
        clients still advance and the process survives; the failed run was
        persisted before its side effect, so the next pass retries it (SPEC.md
        sections 7 and 11).
        """

        moment = on if on is not None else self._clock()
        advanced: list[WorkflowRun] = []
        for tenant_id in self._tenants:
            try:
                advanced.extend(
                    self._handler.resume_due(
                        tenant_id=tenant_id,
                        actor=self._actor,
                        reason=self._reason,
                        on=moment,
                        correlation_id=self._correlation_id_factory(),
                    )
                )
            except Exception:  # noqa: BLE001 - one client must not stop the loop
                self._log.exception(
                    "workflow resume pass failed for client %r; its runs stay "
                    "persisted and are retried on the next pass",
                    tenant_id,
                )
        return tuple(advanced)

    def serve(
        self,
        *,
        stop: threading.Event,
        interval_seconds: float = DEFAULT_TICK_SECONDS,
    ) -> None:
        """Run resume passes until ``stop`` is set (SPEC.md section 7)."""

        self._log.info(
            "RED workflow worker started for clients %s", ", ".join(self._tenants)
        )
        while not stop.is_set():
            self.run_once()
            stop.wait(interval_seconds)
        self._log.info("RED workflow worker stopped")


def _new_correlation_id() -> str:
    return f"worker-{uuid4().hex}"


def worker_from_env(
    environ: Mapping[str, str],
    *,
    transport: ConnectorTransport | None = None,
) -> WorkflowWorker:
    """Build the worker from configuration (SPEC.md sections 6 and 10).

    The same ``DATABASE_URL`` selects the durable run store and the durable
    external operation store, so a run resumed by the worker and a status read by
    the API share one database. The connector transport is injected for tests; a
    deployment must configure a real one.
    """

    database_url = environ.get("DATABASE_URL")
    chosen_transport = (
        transport if transport is not None else connector_transport_from_env(environ)
    )
    connector: ConnectorPort = IdempotentConnector(
        store=external_operation_store_from_env(database_url),
        transport=chosen_transport,
    )
    executor = ConnectorStepExecutor(
        connector=connector,
        connector_name=environ.get("REDOP_CONNECTOR_NAME") or DEFAULT_CONNECTOR_NAME,
    )
    return build_worker(
        store=workflow_run_store_from_env(database_url),
        executor=executor,
        tenants=parse_tenant_roster(environ.get("REDOP_WORKER_TENANTS")),
        actor=environ.get("REDOP_WORKER_ACTOR") or DEFAULT_ACTOR,
    )


def main() -> int:
    """Entry point for ``python -m redops.worker`` (SPEC.md section 7)."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    stop = threading.Event()

    def _request_stop(signum: int, _frame: object) -> None:
        logger.info(
            "received signal %s; stopping after the current pass", signum
        )
        stop.set()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    worker = worker_from_env(os.environ)
    worker.serve(stop=stop, interval_seconds=_tick_seconds(os.environ))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
