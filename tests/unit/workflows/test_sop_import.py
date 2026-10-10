"""Tests for the canon SOP/playbook workflow import (K14; SPEC.md section 7).

The importer turns the pinned canon's operating procedures into versioned
workflow definitions: procedure items become task steps, a role whose duty says
it approves becomes a human approval gate, and the version is derived from the
source content so a canon change advances it instead of drifting. The generated
modules feed RED's durable definition registry (startable, gate-bound runs) and
the cockpit's Jobs catalog. Nothing here approves, spends or deploys.
"""

from __future__ import annotations
import os
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CANON_DIR = Path(os.environ.get("RALPH_CANON", str(REPO_ROOT.parent / "canon")))

SOP_TEXT = """# Ad campaign setup SOP

This procedure sets up and launches one simple ad campaign.

## Trigger

The funnel is live.

## Roles

- Ads specialist: builds and runs the campaign.
- Client: approves the budget.

## Procedure

1. Set up tracking, audiences, and goals.
2. Build one campaign.
3. Launch the campaign.

## Decision points

- If leads are cheap but do not book, check the funnel.

## Records

Save the campaign settings in the client folder.
"""


class ParseOpsDocumentTests(unittest.TestCase):
    def test_parses_sections_into_structured_parts(self) -> None:
        from redops.workflows.sop_import import parse_ops_document

        doc = parse_ops_document(SOP_TEXT, Path("sops/ad-campaign-setup.md"))
        self.assertEqual(doc.slug, "ad-campaign-setup")
        self.assertEqual(doc.kind, "sop")
        self.assertEqual(doc.title, "Ad campaign setup SOP")
        self.assertEqual(
            doc.roles,
            (("Ads specialist", "builds and runs the campaign."), ("Client", "approves the budget.")),
        )
        self.assertEqual(
            doc.procedure,
            ("Set up tracking, audiences, and goals.", "Build one campaign.", "Launch the campaign."),
        )
        self.assertEqual(doc.decisions, ("If leads are cheap but do not book, check the funnel.",))
        self.assertEqual(len(doc.content_sha), 64)

    def test_playbook_kind_follows_the_source_directory(self) -> None:
        from redops.workflows.sop_import import parse_ops_document

        doc = parse_ops_document(SOP_TEXT, Path("playbooks/funnel.md"))
        self.assertEqual(doc.kind, "playbook")


class DeriveDefinitionTests(unittest.TestCase):
    def test_procedure_items_become_task_steps_and_an_approving_role_becomes_a_gate(self) -> None:
        from redops.workflows.sop_import import (
            definition_id,
            derive_definition,
            parse_ops_document,
        )
        from redops.workflows.domain.value_objects import WorkflowStepKind

        doc = parse_ops_document(SOP_TEXT, Path("sops/ad-campaign-setup.md"))
        definition = derive_definition(doc)
        self.assertEqual(definition.definition_id, definition_id(doc))
        self.assertEqual(definition.definition_id, "red-sop-ad-campaign-setup")
        self.assertEqual(definition.version, f"1.{doc.content_sha[:8]}")
        kinds = [step.kind for step in definition.steps]
        self.assertEqual(kinds.count(WorkflowStepKind.TASK), 3)
        self.assertEqual(kinds.count(WorkflowStepKind.APPROVAL), 1)
        self.assertEqual(definition.steps[-1].name, "gate-client")

    def test_a_document_with_no_approving_role_has_no_gate(self) -> None:
        from redops.workflows.sop_import import parse_ops_document, derive_definition
        from redops.workflows.domain.value_objects import WorkflowStepKind

        text = SOP_TEXT.replace("approves the budget.", "owns the budget.")
        doc = parse_ops_document(text, Path("sops/ad-campaign-setup.md"))
        definition = derive_definition(doc)
        self.assertNotIn(WorkflowStepKind.APPROVAL, [step.kind for step in definition.steps])

    def test_step_names_are_unique_across_procedure_and_gates(self) -> None:
        from redops.workflows.sop_import import parse_ops_document, derive_definition

        doc = parse_ops_document(SOP_TEXT, Path("sops/ad-campaign-setup.md"))
        names = [step.name for step in derive_definition(doc).steps]
        self.assertEqual(len(names), len(set(names)))


class RegistryTests(unittest.TestCase):
    def test_every_generated_document_builds_a_valid_definition(self) -> None:
        from redops.workflows.sop_library import ops_workflow_definitions

        definitions = ops_workflow_definitions()
        self.assertGreaterEqual(len(definitions), 50)
        for definition in definitions.values():
            self.assertTrue(definition.steps)
            names = [step.name for step in definition.steps]
            self.assertEqual(len(names), len(set(names)))

    def test_the_merged_registry_resolves_an_imported_sop(self) -> None:
        from redops.workflows.pipeline import RED_WORKFLOW_DEFINITIONS, red_workflow_definition
        from redops.workflows.domain.value_objects import WorkflowStepKind

        self.assertIn("red-stage-0-10-pipeline", RED_WORKFLOW_DEFINITIONS)
        self.assertIn("red-sop-ad-campaign-setup", RED_WORKFLOW_DEFINITIONS)
        definition = red_workflow_definition("red-sop-ad-campaign-setup")
        self.assertIn(WorkflowStepKind.APPROVAL, [step.kind for step in definition.steps])

    def test_the_cockpit_jobs_registry_lists_the_imported_documents(self) -> None:
        from openexecutive.workflows import WORKFLOW_REGISTRY
        from openexecutive.workflows.redops_sops import build_red_ops_workflows
        from openexecutive.workflows.base import WorkflowSection

        built = build_red_ops_workflows()
        self.assertGreaterEqual(len(built), 50)
        for name, workflow in built.items():
            self.assertIn(name, WORKFLOW_REGISTRY)
            self.assertIs(workflow.section, WorkflowSection.RED)
            self.assertTrue(workflow.steps())

    def test_generated_modules_match_the_pinned_canon(self) -> None:
        if not (CANON_DIR / "docs" / "ops").is_dir():
            self.skipTest("canon directory not available")
        from redops.workflows import sop_import

        docs = sop_import.collect_canon_ops(CANON_DIR)
        self.assertTrue(docs)
        red_gen = (REPO_ROOT / "backend" / "redops" / "workflows" / "ops_documents_gen.py").read_text(
            encoding="utf-8"
        )
        cockpit_gen = (
            REPO_ROOT
            / "vendor"
            / "openexecutive"
            / "packages"
            / "core"
            / "openexecutive"
            / "workflows"
            / "redops_sops.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(red_gen, sop_import.render_red_module(docs))
        self.assertEqual(cockpit_gen, sop_import.render_cockpit_module(docs))


if __name__ == "__main__":
    unittest.main()
