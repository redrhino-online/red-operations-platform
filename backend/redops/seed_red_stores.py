"""Seed the RED runtime Departments/Council/People stores (K10; SPEC.md section
14 condition 7, ADR 0006).

The vendored cockpit seeds eight generic C-suite departments on first run
(``openexecutive.departments.store.seed_default_departments``). RED's roster is
the nine section 5 agents plus the chartered proposal-only capability slots 10
and 11, so this seed replaces the generic defaults with RED's departments,
driving the vendored store through its public API only — no vendor file is
modified (ADR 0014). It is idempotent: a rerun changes nothing.

Each department's charter is parsed from the agent charter the charter gate
requires (``docs/agents/charter-*.md``): the ``## Mission`` section becomes the
department mission, the ``## Responsibilities`` "Owns:" bullets become the
charter scope and the "Does not own:" bullets become out-of-scope. Capability
slots 10 and 11 carry no specialist key, so they render as informational rows
and are never routed (proposal-only, ADR 0006).

The Council surface is the agent roster the guide already renders RED
(``guide/prebuilt/council.json``, C4) and this seed aligns the runtime
departments with it: the nine specialist keys are exactly
``agents.redops_agents.RED_SPECIALIST_AREAS``. The People store is left empty on
purpose — RED invents no humans, and the human approvers are owner decisions
(SPEC.md section 11) — so after this seed every Departments/Council/People
surface renders RED only.

Usage: ``python -m redops.seed_red_stores`` seeds the database named by
``EPISODIC_DB_PATH`` (the vendored stores' default). It approves nothing, spends
nothing and deploys nothing.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

from openexecutive.departments import store
from openexecutive.departments.charters import DEFAULT_DEPARTMENTS
from openexecutive.departments.models import AuthorityLevel, DepartmentCharter

REPO_ROOT = Path(__file__).resolve().parents[2]
CHARTER_DIR = REPO_ROOT / "docs" / "agents"


@dataclass(frozen=True)
class RedDepartment:
    """One RED agent as a runtime department (SPEC.md section 5)."""

    slot: int
    title: str
    specialist_key: str | None
    charter_file: str


# The nine core agents route through the RED specialist registry; the chartered
# capability slots 10 and 11 are proposal-only and carry no specialist key, so
# they are never routed (ADR 0006).
RED_DEPARTMENTS: tuple[RedDepartment, ...] = (
    RedDepartment(1, "Discovery and Diagnosis", "discovery", "charter-01-discovery-diagnosis.md"),
    RedDepartment(2, "IP Structuring", "ip_structuring", "charter-02-ip-structuring.md"),
    RedDepartment(3, "Offer and Journey Design", "offer_journey", "charter-03-offer-journey-design.md"),
    RedDepartment(4, "Knowledge Management", "knowledge", "charter-04-knowledge-management.md"),
    RedDepartment(5, "Governance and Approval", "governance", "charter-05-governance-approval.md"),
    RedDepartment(6, "Business Asset Production", "asset_production", "charter-06-asset-production.md"),
    RedDepartment(7, "Campaign and Journey Execution", "campaign_execution", "charter-07-campaign-execution.md"),
    RedDepartment(8, "Insight and Performance", "insight", "charter-08-insight-performance.md"),
    RedDepartment(9, "IP Portfolio Development", "ip_portfolio", "charter-09-ip-portfolio.md"),
    RedDepartment(10, "Client Success and Engagement Health", None, "charter-10-client-success.md"),
    RedDepartment(11, "Assurance, Risk and Compliance", None, "charter-11-assurance-compliance.md"),
)


def _sections(text: str) -> dict[str, str]:
    """Split a charter into its ``## `` sections, whitespace-trimmed."""

    collected: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            collected[current] = []
        elif current is not None:
            collected[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in collected.items()}


def charter_for(spec: RedDepartment) -> DepartmentCharter:
    """Build the department charter from the agent charter file.

    The charter gate (``scripts/check_agent_charters.sh``) requires every agent
    charter to carry ``## Mission`` and ``## Responsibilities`` with "Owns:" and
    "Does not own:" lists, so the mapping below is total over the required
    shape: mission from the Mission section, scope from the Owns bullets and
    out-of-scope from the Does-not-own bullets. A wrapped bullet continues the
    previous one, so no charter text is dropped.
    """

    text = (CHARTER_DIR / spec.charter_file).read_text(encoding="utf-8")
    sections = _sections(text)
    mission = " ".join(sections.get("Mission", "").split())
    owns: list[str] = []
    out_of_scope: list[str] = []
    bucket = owns
    for line in sections.get("Responsibilities", "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith("does not own"):
            bucket = out_of_scope
            continue
        if lowered.startswith("owns"):
            continue
        if stripped.startswith("- "):
            bucket.append(stripped[2:].strip())
        elif bucket:
            bucket[-1] = f"{bucket[-1]} {stripped}"
    return DepartmentCharter(mission=mission, scope=owns, out_of_scope=out_of_scope)


def seed_red_departments(db_path: Path | None = None) -> dict[str, list[str]]:
    """Make the runtime departments RED once; a rerun changes nothing.

    The vendored default seed runs first so a fresh database is initialized and
    its one-time sentinel is marked (the user owns the list afterwards), then
    the generic C-suite defaults are removed and RED's roster is inserted or
    updated through the store's public API. Returns which slugs were removed,
    created and updated; on an already-RED database every list is empty.
    """

    store.initialize_db(db_path)
    store.seed_default_departments(db_path)

    removed: list[str] = []
    for slug, _title, _key, _charter in DEFAULT_DEPARTMENTS:
        if store.delete_department(slug, db_path):
            removed.append(slug)

    states = store.list_departments(db_path)
    by_key = {s.config.specialist_key: s for s in states if s.config.specialist_key}
    by_title = {s.config.title: s for s in states}

    created: list[str] = []
    updated: list[str] = []
    for spec in RED_DEPARTMENTS:
        charter = charter_for(spec)
        current = by_key.get(spec.specialist_key) if spec.specialist_key else None
        if current is None:
            current = by_title.get(spec.title)
        if current is None:
            state = store.create_department(
                spec.title,
                mission=charter.mission,
                specialist_key=spec.specialist_key,
                db_path=db_path,
            )
            store.update_department(
                state.config.slug,
                charter=charter,
                authority_level=AuthorityLevel.PROPOSE_ONLY,
                db_path=db_path,
            )
            created.append(state.config.slug)
        else:
            # Only write when something differs, so a rerun on an already-RED
            # database is a true no-op and the summary stays honest.
            needs_update = (
                current.config.title != spec.title
                or current.config.charter != charter
                or current.config.authority_level != AuthorityLevel.PROPOSE_ONLY
            )
            if needs_update:
                store.update_department(
                    current.config.slug,
                    title=spec.title,
                    charter=charter,
                    authority_level=AuthorityLevel.PROPOSE_ONLY,
                    db_path=db_path,
                )
                updated.append(current.config.slug)

    return {"removed": removed, "created": created, "updated": updated}


def seed_red_stores_from_env() -> dict[str, list[str]]:
    """Seed the database named by ``EPISODIC_DB_PATH`` (or the vendored default)."""

    raw = os.environ.get("EPISODIC_DB_PATH")
    return seed_red_departments(Path(raw) if raw else None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the RED runtime stores (K10).")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="SQLite path (default: EPISODIC_DB_PATH or the vendored default)",
    )
    args = parser.parse_args()
    summary = seed_red_departments(args.db)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
