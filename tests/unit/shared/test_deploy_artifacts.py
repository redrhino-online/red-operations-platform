"""Behavioral tests for the Q47 deploy artifacts (SPEC.md section 13 condition 9).

Condition 9 requires the prototype deployed on the Atlas k3s cluster. The deploy
slice (Q47-Q50) starts with container images and the CI that builds and promotes
them. These tests pin the shape the rest of the slice depends on: the API image
runs the RED app and its ``/red/health`` probe, the UI image runs the Next.js
standalone server that carries the RED identity marker, the build context keeps
the pinned submodule's local ``.venv`` out, and the Gitea workflow builds and
pushes both images and promotes the tag into the GitOps repo.

They are structural guards, not a substitute for the real image build and the
deployed health check; they fail loudly if a rename or a dropped step would
silently break the deploy.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

API_DOCKERFILE = REPO_ROOT / "Dockerfile.api"
UI_DOCKERFILE = REPO_ROOT / "Dockerfile.ui"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
BUILD_WORKFLOW = REPO_ROOT / ".gitea" / "workflows" / "build.yaml"


class ApiImageTest(unittest.TestCase):
    def test_runs_the_red_app_and_health_probe(self) -> None:
        text = API_DOCKERFILE.read_text(encoding="utf-8")

        self.assertIn("redops.api.app:app", text)
        self.assertIn("EXPOSE 8000", text)
        # redops is imported from backend/ via PYTHONPATH, the same way
        # `make check` runs it; the project itself is not installed.
        self.assertIn("PYTHONPATH=/app/backend", text)

    def test_installs_from_the_committed_lock(self) -> None:
        text = API_DOCKERFILE.read_text(encoding="utf-8")

        # --locked fails the build if uv.lock is stale; the editable
        # OpenExecutive source must be present before the sync.
        self.assertIn("uv sync --locked", text)
        self.assertIn("vendor/openexecutive/packages/core/", text)


class UiImageTest(unittest.TestCase):
    def test_runs_the_next_standalone_server(self) -> None:
        text = UI_DOCKERFILE.read_text(encoding="utf-8")

        self.assertIn(".next/standalone", text)
        self.assertIn('CMD ["node", "server.js"]', text)
        self.assertIn("EXPOSE 3000", text)


class BuildContextTest(unittest.TestCase):
    def test_excludes_the_submodule_local_venv(self) -> None:
        text = DOCKERIGNORE.read_text(encoding="utf-8")

        # The pinned submodule is ~1.9 GB, almost all a local .venv that must
        # never enter the build context or an image.
        self.assertIn("**/.venv", text)
        self.assertIn("**/node_modules", text)


class BuildWorkflowTest(unittest.TestCase):
    def test_builds_and_pushes_both_red_images(self) -> None:
        text = BUILD_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("Dockerfile.api", text)
        self.assertIn("Dockerfile.ui", text)
        self.assertIn("registry.atlas.lan", text)
        self.assertIn("redop-api", text)
        self.assertIn("redop-ui", text)

    def test_promotes_the_tag_into_the_gitops_repo(self) -> None:
        text = BUILD_WORKFLOW.read_text(encoding="utf-8")

        # Argo CD reconciles apps/redop/chart from the Gitea GitOps repo; the
        # workflow commits the new apiTag/uiTag so the release is promoted.
        self.assertIn("atlas-admin/atlas.git", text)
        self.assertIn("apps/redop/chart/values.yaml", text)
        self.assertIn("apiTag", text)
        self.assertIn("uiTag", text)


if __name__ == "__main__":
    unittest.main()
