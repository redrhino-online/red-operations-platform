"""Reference adapters for the ``StageArtifactStore`` port.

The process-local adapter exercises the port contract and the application seam
without a database, so the append-only rule (an identical same-key replay is
idempotent and the same key with different content is refused) and tenant
scoping are testable, and the durable PostgreSQL adapter follows the same
contract. ``PostgresStageArtifactStore`` is the durable adapter whose table is
created by migration ``0020_stage_artifacts``; it is exercised wherever a
psycopg driver and a ``DATABASE_URL`` are available (see
``tests/unit/archive/test_stage_artifact_postgres.py``). Row serialisation
lives in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.archive.application.ports import StageArtifactStore
from redops.contexts.archive.domain.entities import StageArtifact
from redops.contexts.archive.domain.errors import (
    StageArtifactVersionConflictError,
    UnscopedStageArtifactError,
)
from redops.contexts.archive.infrastructure.mappers import (
    STAGE_ARTIFACT_COLUMNS,
    artifact_from_row,
    artifact_to_row,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]


class StageArtifactConfigurationError(RuntimeError):
    """The stage artifact store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept
    an archived artifact that vanishes on restart, so a missing psycopg driver
    is a configuration error rather than a degraded mode (SPEC.md sections 3, 4
    and 9).
    """


def _require_artifact_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's archived artifacts.

    SPEC.md sections 3 and 9 make an archived artifact a client resource that
    must carry its tenant on every command and query; storing or listing one
    without a client would either leak across clients or create an orphaned
    record.
    """

    if not value or not value.strip():
        raise UnscopedStageArtifactError(
            f"a tenant-scoped stage artifact {operation} requires a non-blank "
            "tenant id; an archived artifact is a client resource and cannot "
            "be stored or read unscoped"
        )


def _artifact_matches(
    artifact: StageArtifact,
    *,
    workspace_id: str | None,
    stage_number: int | None,
    kind: str | None,
    asset_id: str | None,
) -> bool:
    """Apply the optional list filters as equality matches."""

    return (
        (workspace_id is None or artifact.workspace_id == workspace_id)
        and (stage_number is None or artifact.stage_number == stage_number)
        and (kind is None or artifact.kind == kind)
        and (asset_id is None or artifact.asset_id == asset_id)
    )


def _artifact_order(artifact: StageArtifact) -> tuple[int, str, str, int]:
    """Order artifacts by stage, kind, asset and newest version first."""

    return (artifact.stage_number, artifact.kind, artifact.asset_id, -artifact.version)


class InMemoryStageArtifactStore(StageArtifactStore):
    """Append-only, process-local artifact store keyed by the archive key."""

    def __init__(self) -> None:
        self._artifacts: dict[tuple[str, str, str, int], StageArtifact] = {}

    def save(self, artifact: StageArtifact) -> None:
        _require_artifact_tenant(artifact.tenant_id, "write")
        key = (
            artifact.tenant_id,
            artifact.workspace_id,
            artifact.asset_id,
            artifact.version,
        )
        existing = self._artifacts.get(key)
        if existing is not None:
            if existing != artifact:
                raise StageArtifactVersionConflictError(
                    f"stage artifact {artifact.asset_id!r} version "
                    f"{artifact.version} is already archived for workspace "
                    f"{artifact.workspace_id!r} of tenant "
                    f"{artifact.tenant_id!r} with different content; the "
                    "archive is append-only, so a change is dropped as a new "
                    "version"
                )
            return
        self._artifacts[key] = artifact

    def list(
        self,
        tenant_id: str,
        workspace_id: str | None = None,
        stage_number: int | None = None,
        kind: str | None = None,
        asset_id: str | None = None,
    ) -> tuple[StageArtifact, ...]:
        _require_artifact_tenant(tenant_id, "read")
        selected = [
            artifact
            for artifact in self._artifacts.values()
            if artifact.tenant_id == tenant_id
            and _artifact_matches(
                artifact,
                workspace_id=workspace_id,
                stage_number=stage_number,
                kind=kind,
                asset_id=asset_id,
            )
        ]
        selected.sort(key=_artifact_order)
        return tuple(selected)

    def next_version(self, tenant_id: str, workspace_id: str, asset_id: str) -> int:
        _require_artifact_tenant(tenant_id, "version allocation")
        versions = [
            key[3]
            for key in self._artifacts
            if key[0] == tenant_id
            and key[1] == workspace_id
            and key[2] == asset_id
        ]
        return max(versions, default=0) + 1

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresStageArtifactStore(StageArtifactStore):
    """Durable, append-only stage artifact store backed by PostgreSQL.

    Rows are created by migration ``0020_stage_artifacts`` and are scoped by a
    NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``list`` reads
    only the requested tenant's rows and rebuilds the aggregate through
    ``artifact_from_row``, so a stored row the aggregate would reject raises on
    load rather than being read back as a real artifact. ``save`` inserts a new
    artifact and treats an identical same-key replay as idempotent while
    refusing a same-key row with different content: the archive is append-only
    and a change is a new version (docs/specs/stage-artifact-archive.md section
    1.1). Row-level security (ADR 0004) is a follow-up; tenant scoping is
    enforced here by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL stage artifact adapter requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def list(
        self,
        tenant_id: str,
        workspace_id: str | None = None,
        stage_number: int | None = None,
        kind: str | None = None,
        asset_id: str | None = None,
    ) -> tuple[StageArtifact, ...]:
        _require_artifact_tenant(tenant_id, "read")
        clauses = ["tenant_id = %s"]
        params: list[Any] = [tenant_id]
        for column, value in (
            ("workspace_id", workspace_id),
            ("stage_number", stage_number),
            ("kind", kind),
            ("asset_id", asset_id),
        ):
            if value is not None:
                clauses.append(f"{column} = %s")
                params.append(value)
        columns = ", ".join(STAGE_ARTIFACT_COLUMNS)
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {columns}
                FROM stage_artifacts
                WHERE {" AND ".join(clauses)}
                ORDER BY stage_number, kind, asset_id, version DESC
                """,
                tuple(params),
            )
            rows = cursor.fetchall()
        return tuple(artifact_from_row(row) for row in rows)

    def _stored(self, artifact: StageArtifact) -> StageArtifact | None:
        columns = ", ".join(STAGE_ARTIFACT_COLUMNS)
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {columns}
                FROM stage_artifacts
                WHERE tenant_id = %s
                  AND workspace_id = %s
                  AND asset_id = %s
                  AND version = %s
                """,
                (
                    artifact.tenant_id,
                    artifact.workspace_id,
                    artifact.asset_id,
                    artifact.version,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return artifact_from_row(row)

    def save(self, artifact: StageArtifact) -> None:
        _require_artifact_tenant(artifact.tenant_id, "write")
        existing = self._stored(artifact)
        if existing is not None:
            if existing != artifact:
                raise StageArtifactVersionConflictError(
                    f"stage artifact {artifact.asset_id!r} version "
                    f"{artifact.version} is already archived for workspace "
                    f"{artifact.workspace_id!r} of tenant "
                    f"{artifact.tenant_id!r} with different content; the "
                    "archive is append-only, so a change is dropped as a new "
                    "version"
                )
            return
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO stage_artifacts (
                    {", ".join(STAGE_ARTIFACT_COLUMNS)}
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                artifact_to_row(artifact),
            )
        self._connection.commit()

    def next_version(self, tenant_id: str, workspace_id: str, asset_id: str) -> int:
        _require_artifact_tenant(tenant_id, "version allocation")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(MAX(version), 0)
                FROM stage_artifacts
                WHERE tenant_id = %s
                  AND workspace_id = %s
                  AND asset_id = %s
                """,
                (tenant_id, workspace_id, asset_id),
            )
            highest = cursor.fetchone()[0]
        return int(highest) + 1

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def stage_artifact_store_from_env(
    database_url: str | None,
) -> StageArtifactStore:
    """Select the stage artifact store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so an
    archived artifact survives a restart and is shared across the API and
    worker processes (docs/specs/stage-artifact-archive.md section 1.2); without
    one the process-local reference adapter keeps local development and the
    domain-only test interpreter working. A set but unusable configuration
    raises ``StageArtifactConfigurationError`` so a deployment cannot mistake a
    non-durable store for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryStageArtifactStore()
    if psycopg is None:
        raise StageArtifactConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to "
            "use the process-local stage artifact store"
        )
    return PostgresStageArtifactStore(psycopg.connect(database_url))
