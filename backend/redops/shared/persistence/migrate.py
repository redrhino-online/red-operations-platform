"""Programmatic migration runner for RED's PostgreSQL schema.

ADR 0003: RED's schema changes ship as migrations committed with the code.
SPEC.md section 10 requires the deployment to apply them as a distinct step
before the API serves traffic, with a scoped account, and to keep schema
migrations under manual approval until rollback is proven; it also says Argo CD
health checks must wait for migrations and rollout readiness. This module is the
command that step runs::

    python -m redops.shared.persistence.migrate

It reads ``DATABASE_URL`` from the environment and applies ``alembic upgrade
head`` against the committed migration set. Paths are resolved relative to this
module, so the runner works from any working directory (the container's ``/app``
as well as the repository root).

The FastAPI app deliberately does not call this at startup. Running schema
changes from a web process would race across workers and would let an
unreviewed image apply migrations, which SPEC.md section 10 forbids until
rollback is proven. The migration step is its own reviewed, scoped command; the
app only uses the schema once it exists.
"""

from __future__ import annotations

import os
from pathlib import Path

try:  # alembic is an app dependency; the domain-only test env lacks it.
    from alembic import command
    from alembic.config import Config
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    command = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]


class MigrationConfigurationError(RuntimeError):
    """The migration step was invoked without a usable configuration.

    A blank ``DATABASE_URL`` is a misconfiguration, not a request to skip the
    schema step: silently doing nothing would let the API start against a
    database with no ``gate_decisions`` table and fail on the first gate write
    (SPEC.md sections 3, 4 and 10). A missing alembic install is the same class
    of error.
    """


_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_BACKEND_DIR = _MIGRATIONS_DIR.parents[3]


def _normalise_url(database_url: str) -> str:
    """Return a SQLAlchemy URL using the psycopg 3 driver.

    The platform supplies a plain ``postgresql://`` URL, so the driver dialect is
    normalised here, matching the Alembic environment.
    """

    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://") :]
    return database_url


def _alembic_url(database_url: str) -> str:
    """Return the URL safe to hand to alembic's configparser.

    alembic's ``Config`` is a configparser, which treats ``%`` as interpolation
    syntax, so a percent-encoded password (e.g. ``%2F``) raises
    ``ValueError: invalid interpolation syntax``. Escaping ``%`` as ``%%`` lets
    configparser decode it back to the original URL, which SQLAlchemy/psycopg
    then decode to the raw password.
    """

    return _normalise_url(database_url).replace("%", "%%")


def run_migrations(database_url: str | None = None) -> None:
    """Apply every committed migration up to ``head``.

    ``database_url`` defaults to the ``DATABASE_URL`` environment variable, the
    contract SPEC.md section 10 sets for the platform. Raises
    ``MigrationConfigurationError`` before touching the database when the URL is
    blank or alembic is unavailable.
    """

    url = database_url if database_url is not None else os.environ.get("DATABASE_URL")
    if not url or not url.strip():
        raise MigrationConfigurationError(
            "run_migrations requires a non-blank DATABASE_URL (SPEC.md section 10)"
        )
    if command is None or Config is None:
        raise MigrationConfigurationError(
            "alembic is required to apply migrations; install the app dependencies"
        )

    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS_DIR))
    config.set_main_option("prepend_sys_path", str(_BACKEND_DIR))
    config.set_main_option("path_separator", "os")
    # alembic's Config is a configparser, which treats `%` as interpolation
    # syntax. A percent-encoded password (e.g. `%2F`) must be escaped so it
    # reaches SQLAlchemy unchanged; psycopg decodes it back to the raw password.
    config.set_main_option("sqlalchemy.url", _alembic_url(url))
    command.upgrade(config, "head")


def main() -> int:
    """Entry point for ``python -m redops.shared.persistence.migrate``."""

    run_migrations()
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
