"""Import the pinned canon's SOPs and playbooks as versioned workflow definitions.

Item K14 (IMPLEMENTATION_PLAN.md): the canon's operating procedures -
``docs/ops/sops/`` and ``docs/ops/playbooks/`` - become workflow definitions so
the cockpit's Jobs catalog lists them and durable, gate-bound runs of them start
through RED's workflow API. The importer is a build-time tool: the API and
cockpit images do not ship the canon, so it derives deterministic, committed
modules from the pinned canon content instead of reading files at runtime.

Derivation rules (deterministic, derived from the document so nothing is
self-declared):
- every numbered ``## Procedure`` item becomes a ``TASK`` step (``step-01``...);
- every role whose duty says it approves (``## Roles``) becomes an ``APPROVAL``
  step (``gate-<role>``) - a human gate the K12 binding advances with a RED
  approval; a document with no approving role has no gate and runs through;
- the definition version is ``1.<sha256-8>`` of the source text, so a canon
  change advances the version instead of silently drifting.

The importer writes two committed modules: the RED-side metadata module
(``ops_documents_gen.py``) the durable definition registry builds from, and the
cockpit catalog module (``redops_sops.py``) the Jobs registry builds from. It
approves nothing, spends nothing and deploys nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

PROCEDURE_ITEM = re.compile(r"^\s*\d+\.\s+(.*)$")
BULLET_ITEM = re.compile(r"^\s*-\s+(.*)$")
ROLE_ITEM = re.compile(r"^\s*-\s+([A-Za-z ][A-Za-z /-]*?):\s*(.*)$")
APPROVAL_DUTY = re.compile(r"\bapprov", re.IGNORECASE)
HEADING = re.compile(r"^##\s+(.*)$")

RED_MODULE_PATH = Path("backend/redops/workflows/ops_documents_gen.py")
COCKPIT_MODULE_PATH = Path(
    "vendor/openexecutive/packages/core/openexecutive/workflows/redops_sops.py"
)


@dataclass(frozen=True)
class OpsDocument:
    """One parsed canon operating procedure or playbook."""

    slug: str
    kind: str
    title: str
    summary: str
    roles: tuple[tuple[str, str], ...]
    procedure: tuple[str, ...]
    decisions: tuple[str, ...]
    content_sha: str


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_ops_document(text: str, source: Path) -> OpsDocument:
    """Parse one canon ops markdown document into its structured parts."""

    lines = text.splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), source.stem)
    sections: dict[str, list[str]] = {}
    current = ""
    for line in lines:
        match = HEADING.match(line)
        if match:
            current = match.group(1).strip().lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    roles: list[tuple[str, str]] = []
    for line in sections.get("roles", []):
        match = ROLE_ITEM.match(line)
        if match:
            roles.append((match.group(1).strip(), match.group(2).strip()))
    procedure: list[str] = []
    # SOPs number their work under ``## Procedure``; playbooks under
    # ``## Steps``. Both are the same ordered, numbered list shape.
    for section_name in ("procedure", "steps"):
        for line in sections.get(section_name, []):
            match = PROCEDURE_ITEM.match(line)
            if match:
                procedure.append(" ".join(match.group(1).split()))
    decisions: list[str] = []
    for line in sections.get("decision points", []):
        match = BULLET_ITEM.match(line)
        if match:
            decisions.append(" ".join(match.group(1).split()))
    summary = " ".join(
        line.strip() for line in lines[1:] if line.strip() and not line.startswith("#")
    )[:300]
    kind = "sop" if source.parent.name == "sops" else "playbook"
    return OpsDocument(
        slug=source.stem,
        kind=kind,
        title=title,
        summary=summary,
        roles=tuple(roles),
        procedure=tuple(procedure),
        decisions=tuple(decisions),
        content_sha=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def definition_id(doc: OpsDocument) -> str:
    return f"red-{doc.kind}-{_slug(doc.slug)}"


def derive_definition(doc: OpsDocument):
    """Derive the versioned workflow definition from one parsed document.

    Imported lazily so the parser stays importable on the py3.10 domain-only
    environment (the value objects need the full app environment).
    """

    from redops.workflows.domain.value_objects import (
        WorkflowDefinition,
        WorkflowStep,
        WorkflowStepKind,
    )

    steps: list[WorkflowStep] = []
    for index, _item in enumerate(doc.procedure, start=1):
        steps.append(WorkflowStep(name=f"step-{index:02d}", kind=WorkflowStepKind.TASK))
    for role, duty in doc.roles:
        if APPROVAL_DUTY.search(duty):
            steps.append(
                WorkflowStep(name=f"gate-{_slug(role)}", kind=WorkflowStepKind.APPROVAL)
            )
    if not steps:
        steps.append(WorkflowStep(name="step-01", kind=WorkflowStepKind.TASK))
    return WorkflowDefinition(
        definition_id=definition_id(doc),
        version=f"1.{doc.content_sha[:8]}",
        steps=tuple(steps),
    )


def step_titles(doc: OpsDocument) -> dict[str, str]:
    """Human-readable titles for the derived steps, in definition order."""

    titles: dict[str, str] = {}
    for index, item in enumerate(doc.procedure, start=1):
        titles[f"step-{index:02d}"] = item
    for role, duty in doc.roles:
        if APPROVAL_DUTY.search(duty):
            titles[f"gate-{_slug(role)}"] = f"{role} approval: {duty}"
    return titles


def collect_canon_ops(canon_dir: Path) -> list[OpsDocument]:
    """Every SOP and playbook under the canon's ``docs/ops`` tree, sorted."""

    docs: list[OpsDocument] = []
    ops = canon_dir / "docs" / "ops"
    for subdir in ("sops", "playbooks"):
        directory = ops / subdir
        if not directory.is_dir():
            continue
        for source in sorted(directory.glob("*.md")):
            docs.append(parse_ops_document(source.read_text(encoding="utf-8"), source))
    return docs


def document_meta(doc: OpsDocument, *, cockpit: bool) -> dict:
    """The serializable metadata one document contributes to a generated module."""

    definition = derive_definition(doc)
    titles = step_titles(doc)
    steps = [
        {"name": step.name, "kind": step.kind.value, "title": titles.get(step.name, step.name)}
        for step in definition.steps
    ]
    meta: dict = {
        "definition_id": definition.definition_id,
        "kind": doc.kind,
        "title": doc.title,
        "summary": doc.summary,
        "version": definition.version,
        "decisions": list(doc.decisions),
        "steps": steps,
    }
    if not cockpit:
        meta["slug"] = doc.slug
        meta["source"] = (
            "docs/ops/" + ("sops" if doc.kind == "sop" else "playbooks") + "/" + doc.slug + ".md"
        )
        meta["roles"] = [list(pair) for pair in doc.roles]
    return meta


def _meta_literal(docs: list[OpsDocument], *, cockpit: bool) -> str:
    entries = []
    for doc in docs:
        meta = document_meta(doc, cockpit=cockpit)
        body = ",\n".join(f"        {key!r}: {value!r}" for key, value in meta.items())
        entries.append("    {\n" + body + ",\n    }")
    return ",\n".join(entries)


def render_red_module(docs: list[OpsDocument]) -> str:
    lines = [
        '"""Generated canon ops workflow metadata (K14; ADR 0014). DO NOT EDIT.',
        "",
        "Regenerate with:",
        "  uv run python -m redops.workflows.sop_import --canon <RALPH_CANON> \\",
        "      --red-out backend/redops/workflows/ops_documents_gen.py \\",
        "      --cockpit-out vendor/openexecutive/packages/core/openexecutive/workflows/redops_sops.py",
        '"""',
        "",
        "# Metadata derived from the pinned canon's docs/ops/sops and docs/ops/playbooks.",
        "# ``sop_library`` builds the durable workflow definitions from this data; the",
        "# cockpit catalog builds its Jobs entries from the same shapes.",
        "",
        "OPS_DOCUMENT_META: tuple[dict, ...] = (",
        _meta_literal(docs, cockpit=False) + ",",
        ")",
        "",
    ]
    return "\n".join(lines)


def render_cockpit_module(docs: list[OpsDocument]) -> str:
    lines = [
        '"""RED canon ops workflows as cockpit Jobs catalog entries (K14).',
        "",
        "Additive generated file (ADR 0014; the workflows subtree is a RED-owned",
        "surface per the owner-approved exception recorded in",
        "docs/fork_inventory.md). Generated by ``redops.workflows.sop_import`` from",
        "the pinned canon's SOPs and playbooks - do not edit by hand. Each entry",
        "renders its procedure as the plan artifact; the durable, gate-bound runs",
        "are RED versioned workflow runs started through RED's workflow API.",
        "Approves nothing, spends nothing and deploys nothing.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any, AsyncIterator",
        "",
        "from pydantic import BaseModel, Field",
        "",
        "from openexecutive.knowledge.store import ChromaDBStore",
        "from openexecutive.workflows.base import (",
        "    Workflow,",
        "    WorkflowEvent,",
        "    WorkflowSection,",
        "    WorkflowStepDef,",
        ")",
        "",
        "OPS_DOCUMENT_META: tuple[dict, ...] = (",
        _meta_literal(docs, cockpit=True) + ",",
        ")",
        "",
        "",
        "class RedOpsDocumentInputs(BaseModel):",
        '    tenant_id: str = Field(description="The client tenant the run is for")',
        "",
        "",
        "class RedOpsDocumentWorkflow(Workflow):",
        '    """One canon SOP or playbook as a Jobs catalog entry."""',
        "",
        "    def __init__(self, meta: dict) -> None:",
        "        self._meta = meta",
        '        self.name = meta["definition_id"]',
        '        kind_label = "SOP" if meta["kind"] == "sop" else "Playbook"',
        "        self.title = f\"{kind_label}: {meta['title']}\"",
        '        self.description = meta["summary"] or self.title',
        "        self.section = WorkflowSection.RED",
        "        self.estimated_minutes = 3",
        "",
        "    def input_model(self) -> type[BaseModel]:",
        "        return RedOpsDocumentInputs",
        "",
        "    def steps(self) -> list[WorkflowStepDef]:",
        "        return [",
        "            WorkflowStepDef(",
        '                id=step["name"],',
        '                title=step["title"],',
        "                description=(",
        '                    "RED approval gate" if step["kind"] == "approval" else "Procedure step"',
        "                ),",
        "            )",
        '            for step in self._meta["steps"]',
        "        ]",
        "",
        "    async def run(",
        "        self, inputs: BaseModel, store: ChromaDBStore",
        "    ) -> AsyncIterator[Any]:",
        "        meta = self._meta",
        '        for step in meta["steps"]:',
        "            yield WorkflowEvent(",
        '                type="step_start", step_id=step["name"], step_title=step["title"]',
        "            )",
        "            summary = (",
        '                "human approval gate" if step["kind"] == "approval" else "procedure step"',
        "            )",
        '            yield WorkflowEvent(type="step_done", step_id=step["name"], summary=summary)',
        "        lines = [f\"# {meta['title']}\", \"\"]",
        '        lines.append(meta["summary"])',
        '        lines.append("")',
        '        lines.append("## Procedure")',
        '        lines.append("")',
        '        for step in meta["steps"]:',
        '            marker = "gate" if step["kind"] == "approval" else "step"',
        "            lines.append(f\"- **{step['title']}** (`{step['name']}`) - {marker}\")",
        '        if meta["decisions"]:',
        '            lines.append("")',
        '            lines.append("## Decision points")',
        '            lines.append("")',
        '            for decision in meta["decisions"]:',
        '                lines.append(f"- {decision}")',
        '        lines.append("")',
        "        lines.append(",
        '            "Durable, gate-bound runs are RED versioned workflow runs, started "',
        '            "through RED\'s workflow API and read by the workflow run detail "',
        '            "screen. This catalog entry executes nothing and approves nothing."',
        "        )",
        '        yield WorkflowEvent(type="artifact", content="\\n".join(lines))',
        '        yield WorkflowEvent(type="done", run_id=meta["definition_id"])',
        "",
        "",
        "def build_red_ops_workflows() -> dict[str, Workflow]:",
        "    return {",
        '        meta["definition_id"]: RedOpsDocumentWorkflow(meta)',
        "        for meta in OPS_DOCUMENT_META",
        "    }",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canon", required=True, type=Path)
    parser.add_argument("--red-out", required=True, type=Path)
    parser.add_argument("--cockpit-out", required=True, type=Path)
    args = parser.parse_args(argv)
    docs = collect_canon_ops(args.canon)
    if not docs:
        raise SystemExit(f"sop_import: no SOPs or playbooks under {args.canon}/docs/ops")
    args.red_out.write_text(render_red_module(docs), encoding="utf-8")
    args.cockpit_out.write_text(render_cockpit_module(docs), encoding="utf-8")
    sops = sum(doc.kind == "sop" for doc in docs)
    print(
        f"sop_import: imported {len(docs)} documents "
        f"({sops} SOPs, {len(docs) - sops} playbooks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
