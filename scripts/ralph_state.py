#!/usr/bin/env python3
"""Maintain a bounded Ralph handoff and archive older cycle notes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


HISTORY_HEADER = (
    "# Implementation plan history\n\n"
    "Cycle records older than the two current entries in "
    "`IMPLEMENTATION_PLAN.md`. Newest archived entry first.\n\n"
)
STATUS_HEADING = "## Current cycle status"
ENTRY_PATTERN = re.compile(r"^### .+$", re.MULTILINE)
QUEUE_PATTERN = re.compile(r"^\|\s*(G[1-9]|C4|W1|Q16)\s*\|.*$", re.MULTILINE)


def current_status_bounds(lines: list[str]) -> tuple[int, int]:
    start = next(
        (i for i, line in enumerate(lines) if line.rstrip("\n") == STATUS_HEADING),
        None,
    )
    if start is None:
        raise ValueError(f"missing {STATUS_HEADING!r} in IMPLEMENTATION_PLAN.md")
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].startswith("## ")
        ),
        len(lines),
    )
    return start, end


def entry_chunks(section: list[str]) -> tuple[list[str], list[list[str]]]:
    starts = [i for i, line in enumerate(section) if ENTRY_PATTERN.match(line)]
    if not starts:
        raise ValueError("current cycle status has no cycle entries")
    prefix = section[: starts[0]]
    chunks = [
        section[start : starts[n + 1] if n + 1 < len(starts) else len(section)]
        for n, start in enumerate(starts)
    ]
    return prefix, chunks


def rewrite_current_status(plan: str, archived: list[list[str]]) -> str:
    lines = plan.splitlines(keepends=True)
    start, end = current_status_bounds(lines)
    section = lines[start:end]
    prefix, chunks = entry_chunks(section)
    if len(chunks) > 2:
        archived.extend(chunks[2:])
        chunks = chunks[:2]
    note = (
        "\nOlder cycle notes and decisions: `docs/plan-history.md`. Keep only "
        "the latest two cycle entries here; older entries are archived by the "
        "Ralph harness.\n"
    )
    kept = prefix + [line for chunk in chunks for line in chunk]
    if not any("docs/plan-history.md" in line for line in kept):
        kept.extend(["\n", note])
    return "".join(lines[:start] + kept + lines[end:]), archived


def write_history(path: Path, archived: list[list[str]]) -> None:
    if not archived:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if not existing.startswith(HISTORY_HEADER):
            raise ValueError(f"refusing to overwrite unexpected history file: {path}")
        prior = existing[len(HISTORY_HEADER) :]
    else:
        prior = ""
    newest = "".join(line for chunk in archived for line in chunk)
    path.write_text(HISTORY_HEADER + newest + prior, encoding="utf-8")


def compact(value: str, limit: int = 220) -> str:
    value = " ".join(value.strip().split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def field_value(entry: str, field: str) -> str | None:
    lines = entry.splitlines()
    marker = f"- **{field}:**"
    for index, line in enumerate(lines):
        if not line.startswith(marker):
            continue
        values = [line[len(marker) :].strip()]
        for continuation in lines[index + 1 :]:
            if not continuation.strip() or continuation.startswith("- "):
                break
            if continuation.startswith("  "):
                values.append(continuation.strip())
            else:
                break
        return compact(" ".join(values))
    return None


def queue_state(line: str) -> str:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    evidence = cells[-1] if cells else ""
    if re.search(r"unresolved|license-owner request", evidence, re.IGNORECASE):
        status = "blocked on owner input"
    elif re.search(r"\bRemaining:", evidence, re.IGNORECASE):
        status = "partial"
    elif re.search(r"\bDone\s+20\d\d-\d\d-\d\d", evidence, re.IGNORECASE):
        status = "done"
    else:
        status = "open"
    item = compact(cells[1], 72) if len(cells) > 1 else ""
    area = cells[2] if len(cells) > 2 else "?"
    depends = cells[3] if len(cells) > 3 else "?"
    return f"- {cells[0]} [{status}; {area}; depends {depends}]: {item}"


def generate_state(repo: Path) -> str:
    plan_path = repo / "IMPLEMENTATION_PLAN.md"
    plan = plan_path.read_text(encoding="utf-8")
    lines = plan.splitlines(keepends=True)
    start, end = current_status_bounds(lines)
    _, entries = entry_chunks(lines[start:end])
    latest = "".join(entries[0])
    title = entries[0][0].strip()[4:]
    next_item = field_value(latest, "Next ready item")
    selected = field_value(latest, "Selected item")
    outcome = field_value(latest, "Outcome")
    evidence = field_value(latest, "Evidence")

    queue_rows = []
    seen = set()
    for match in QUEUE_PATTERN.finditer(plan):
        identifier = match.group(1)
        if identifier not in seen:
            queue_rows.append(queue_state(match.group(0)))
            seen.add(identifier)

    done_path = repo / ".ralph" / "DONE"
    stop_path = repo / ".ralph" / "STOP"
    history = repo / "docs" / "plan-history.md"
    historical_text = history.read_text(encoding="utf-8") if history.exists() else ""
    has_dod_pass = bool(
        re.search(r"DONE-GATE PASS|definition of done still passes", plan + historical_text, re.I)
    )

    result = [
        "# Ralph state (generated; do not edit)",
        f"- Prototype DoD: {'pass recorded in plan history' if has_dod_pass else 'not recorded as passed'}.",
        f"- Loop markers: STOP={'present' if stop_path.exists() else 'absent'}, DONE={'present' if done_path.exists() else 'absent'}.",
        f"- Latest cycle: {compact(title, 140)}.",
    ]
    for label, value in (
        ("Selected", selected),
        ("Outcome", outcome),
        ("Evidence", evidence),
        ("Next ready", next_item),
    ):
        if value:
            result.append(f"- {label}: {value}")
    if queue_rows:
        result.extend(["", "## Tracked queue"])
        result.extend(queue_rows)
    result.extend(
        [
            "",
            "Read exact plan rows only for selected work. Plan history is "
            "`docs/plan-history.md`.",
        ]
    )
    rendered = "\n".join(result) + "\n"
    if len(rendered.encode("utf-8")) > 4096:
        raise ValueError("generated Ralph state exceeds 4 KB; compact queue rows")
    return rendered


def run(mode: str, repo: Path) -> None:
    plan_path = repo / "IMPLEMENTATION_PLAN.md"
    history_path = repo / "docs" / "plan-history.md"
    if mode in {"initialize", "finish"}:
        plan = plan_path.read_text(encoding="utf-8")
        rewritten, archived = rewrite_current_status(plan, [])
        if rewritten != plan:
            plan_path.write_text(rewritten, encoding="utf-8")
        write_history(history_path, archived)
    state_path = repo / ".ralph" / "STATE.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(generate_state(repo), encoding="utf-8")
    print(f"ralph-state: {mode}: wrote {state_path.relative_to(repo)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "initialize", "finish"), nargs="?", default="prepare")
    parser.add_argument("repo", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    run(args.mode, args.repo.resolve())


if __name__ == "__main__":
    main()
