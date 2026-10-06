"""Behavioral tests for the Q48 RED Helm chart (SPEC.md section 13 condition 9).

Condition 9 requires the prototype deployed on the Atlas k3s cluster. Q48 is the
chart that replaces the OpenExecutive shell in namespace ``redop`` with the RED
API and UI, reusing the existing ``redop-postgres`` database and
``redop-secrets``. These tests pin the shape the rest of the deploy slice
depends on:

* the chart renders, and the migration Job is ordered before the API serves
  (Helm pre-install/pre-upgrade hook, Argo CD PreSync at sync-wave -1, and an
  API initContainer that waits for the Job's success);
* the ingress routes ``/red`` to the API and ``/`` to the UI same-origin;
* the chart reuses the existing database and secrets and provisions no database;
* the worker renders only when explicitly enabled, and stays disabled until a
  connector transport is configured (the entrypoint exists but fails fast
  without one).

The render tests skip when ``helm`` is not on PATH; the structural tests always
run. They are guards, not a substitute for the real cluster release.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CHART_DIR = REPO_ROOT / "deploy" / "charts" / "redop"
TEMPLATES = CHART_DIR / "templates"

HELM = shutil.which("helm")


def _render(extra_args: list[str] | None = None) -> list[dict]:
    """Render the chart and return the parsed manifests."""

    cmd = ["helm", "template", "redop", str(CHART_DIR), "--namespace", "redop"]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def _by_kind(docs: list[dict], kind: str) -> list[dict]:
    return [doc for doc in docs if doc.get("kind") == kind]


def _named(docs: list[dict], kind: str, name: str) -> dict:
    for doc in _by_kind(docs, kind):
        if doc["metadata"]["name"] == name:
            return doc
    raise AssertionError(f"no {kind} named {name!r} in rendered chart")


class ChartStructureTest(unittest.TestCase):
    def test_chart_metadata_and_templates_exist(self) -> None:
        self.assertTrue((CHART_DIR / "Chart.yaml").is_file())
        self.assertTrue((CHART_DIR / "values.yaml").is_file())
        for name in (
            "migration-job.yaml",
            "deployment-api.yaml",
            "deployment-ui.yaml",
            "deployment-worker.yaml",
            "ingress.yaml",
            "pdb.yaml",
        ):
            self.assertTrue((TEMPLATES / name).is_file(), name)

    def test_values_promote_tags_are_top_level(self) -> None:
        # The Gitea build workflow rewrites the exact `apiTag:`/`uiTag:` lines.
        text = (CHART_DIR / "values.yaml").read_text(encoding="utf-8")
        self.assertIn("\napiTag:", "\n" + text)
        self.assertIn("\nuiTag:", "\n" + text)


@unittest.skipUnless(HELM, "helm is not on PATH")
class ChartRenderTest(unittest.TestCase):
    def test_renders_api_ui_and_migration(self) -> None:
        docs = _render()
        _named(docs, "Deployment", "redop-api")
        _named(docs, "Deployment", "redop-ui")
        _named(docs, "Job", "redop-migrate")

    def test_migration_is_ordered_before_the_api_serves(self) -> None:
        docs = _render()
        job = _named(docs, "Job", "redop-migrate")
        annotations = job["metadata"]["annotations"]
        self.assertIn("pre-install", annotations["helm.sh/hook"])
        self.assertIn("pre-upgrade", annotations["helm.sh/hook"])
        self.assertLess(int(annotations["helm.sh/hook-weight"]), 0)
        self.assertEqual(annotations["argocd.argoproj.io/hook"], "PreSync")
        self.assertLess(int(annotations["argocd.argoproj.io/sync-wave"]), 0)

        api = _named(docs, "Deployment", "redop-api")
        self.assertEqual(api["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"], "0")
        init_names = [c["name"] for c in api["spec"]["template"]["spec"]["initContainers"]]
        self.assertIn("wait-for-migration", init_names)
        # The migration Job runs RED's programmatic runner, which resolves the
        # migration directory relative to its module and so needs no
        # `alembic.ini` in the image (the API image does not ship one).
        migrate = job["spec"]["template"]["spec"]["containers"][0]
        self.assertEqual(
            migrate["command"],
            ["python", "-m", "redops.shared.persistence.migrate"],
        )

    def test_migration_job_does_not_need_a_later_created_service_account(self) -> None:
        # The migration Job is an Argo CD PreSync hook, so it runs before the
        # main sync applies the chart's ServiceAccount. It must not reference
        # one, or the hook pod is forbidden and the sync stalls.
        docs = _render()
        job = _named(docs, "Job", "redop-migrate")
        pod_spec = job["spec"]["template"]["spec"]
        self.assertNotIn("serviceAccountName", pod_spec)

    def test_wait_for_migration_reads_the_job_not_the_status_subresource(self) -> None:
        # The Role grants `get` on `jobs` only. Reading the `jobs/status`
        # subresource is forbidden, so the initContainer must read the Job
        # itself (whose body includes status).
        docs = _render()
        api = _named(docs, "Deployment", "redop-api")
        init = api["spec"]["template"]["spec"]["initContainers"][0]
        script = "\n".join(init["command"])
        self.assertIn("/jobs/redop-migrate", script)
        self.assertNotIn("/jobs/redop-migrate/status", script)

    def test_wait_for_migration_tolerates_pretty_printed_job_json(self) -> None:
        # The Kubernetes API returns pretty-printed JSON by default, so the
        # success field is `"succeeded": 1` with a space. A brittle
        # `"succeeded":1` grep never matches and the API pod hangs in Init.
        docs = _render()
        api = _named(docs, "Deployment", "redop-api")
        init = api["spec"]["template"]["spec"]["initContainers"][0]
        script = "\n".join(init["command"])
        self.assertIn('"succeeded"[[:space:]]*:[[:space:]]*[1-9]', script)
        self.assertNotIn('"succeeded":1', script)

    def test_ingress_routes_red_screens_and_root_to_cockpit(self) -> None:
        docs = _render()
        ingress = _named(docs, "Ingress", "redop")
        paths = {
            p["path"]: p["backend"]["service"]["name"]
            for p in ingress["spec"]["rules"][0]["http"]["paths"]
        }
        self.assertEqual(paths["/red"], "redop-api")
        self.assertEqual(paths["/screens"], "redop-ui")
        self.assertEqual(paths["/api/backend"], "redop-cockpit")
        self.assertEqual(paths["/"], "redop-cockpit")

    def test_reuses_existing_database_and_secrets(self) -> None:
        docs = _render()
        # The chart provisions no new database (no StatefulSet), but it must
        # declare the existing Postgres Deployment/Service and both bound PVCs:
        # the Argo CD Application has `prune: true`, so a resource the previous
        # chart created and the RED chart omits would be deleted on sync.
        self.assertEqual(_by_kind(docs, "StatefulSet"), [])
        _named(docs, "Deployment", "redop-postgres")
        _named(docs, "Service", "redop-postgres")
        _named(docs, "PersistentVolumeClaim", "redop-data")
        _named(docs, "PersistentVolumeClaim", "redop-postgres-data")
        api = _named(docs, "Deployment", "redop-api")
        env = {e["name"]: e for e in api["spec"]["template"]["spec"]["containers"][0]["env"]}
        self.assertEqual(
            env["DATABASE_URL"]["valueFrom"]["secretKeyRef"]["name"], "redop-postgres"
        )
        self.assertEqual(
            env["OPENROUTER_API_KEY"]["valueFrom"]["secretKeyRef"]["name"], "redop-secrets"
        )

    def test_api_and_ui_have_probes_and_pdbs(self) -> None:
        docs = _render()
        for name in ("redop-api", "redop-ui"):
            container = _named(docs, "Deployment", name)["spec"]["template"]["spec"]["containers"][0]
            self.assertIn("readinessProbe", container)
            self.assertIn("livenessProbe", container)
        self.assertEqual(len(_by_kind(docs, "PodDisruptionBudget")), 2)

    def test_api_and_ui_replace_on_adoption(self) -> None:
        # The previous chart's Deployments used a different immutable selector,
        # so Argo CD must replace rather than patch them when adopting.
        docs = _render()
        for name in ("redop-api", "redop-ui"):
            annotations = _named(docs, "Deployment", name)["metadata"]["annotations"]
            self.assertEqual(
                annotations["argocd.argoproj.io/sync-options"], "Replace=true"
            )

    def test_worker_is_disabled_by_default_and_enableable(self) -> None:
        default_names = {d["metadata"]["name"] for d in _by_kind(_render(), "Deployment")}
        self.assertNotIn("redop-worker", default_names)
        docs = _render(["--set", "worker.enabled=true"])
        _named(docs, "Deployment", "redop-worker")


if __name__ == "__main__":
    unittest.main()
