"""Behavioral tests for the single-shell cockpit overhaul gate.

SPEC.md section 14 (ADR 0013) requires the rebranded OpenExecutive cockpit to be
the only user-facing RED UI, with the twelve section 8 screens ported to native
`/operations/*` pages as additive files inside the absorbed vendor tree
(ADR 0014) and the separate `/screens` thin client retired. The gate
`scripts/check_cockpit_overhaul.sh` runs as `[7/7]` of `make done`; these tests
pin its contract so it cannot pass while the thin client or a link-out nav group
still exists, and so it cannot demand a live cluster when run offline.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK = REPO_ROOT / "scripts" / "check_cockpit_overhaul.sh"

ROUTES = (
    "command-center",
    "client-workspace",
    "source-explorer",
    "transformation-map",
    "offer-and-journey",
    "build-board",
    "approval-inbox",
    "workflow-run-detail",
    "launch-readiness",
    "performance-review",
    "portfolio-opportunities",
    "authority-settings",
)


def run_check(repo: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["REDOP_HEALTH_URL"] = ""
    return subprocess.run(
        ["bash", str(CHECK), str(repo)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def write_cockpit_ui(repo: Path, *, nav_hrefs: str = "/operations", pages: int = len(ROUTES)) -> None:
    ui = repo / "vendor" / "openexecutive" / "packages" / "ui"
    nav = ui / "src" / "components" / "shell" / "navConfig.ts"
    nav.parent.mkdir(parents=True, exist_ok=True)
    items = ", ".join(
        f'{{ href: "{nav_hrefs}/{route}", label: "{route}" }}' for route in ROUTES
    )
    nav.write_text(
        f'export const NAV_GROUPS = [{{ key: "red", label: "RED Operations", items: [{items}] }}];\n',
        encoding="utf-8",
    )
    (ui / "package.json").write_text(
        '{ "name": "ui", "scripts": { "test": "vitest run" } }\n', encoding="utf-8"
    )
    for route in ROUTES[:pages]:
        page = ui / "src" / "app" / "operations" / route / "page.tsx"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("export default function Page() { return null; }\n", encoding="utf-8")


def build_repo(root: Path, **kwargs) -> Path:
    repo = root / "repo"
    write_cockpit_ui(repo, **kwargs)

    scripts = repo / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "check_definition_of_done.sh").write_text(
        "# single-shell gate stub\n", encoding="utf-8"
    )

    templates = repo / "deploy" / "charts" / "redop" / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / "ingress.yaml").write_text(
        "paths:\n  - path: /\n  - path: /api/backend\n  - path: /red\n", encoding="utf-8"
    )
    (templates / "deployment-api.yaml").write_text("kind: Deployment\n", encoding="utf-8")

    cockpit_tests = repo / "tests" / "cockpit-ui"
    cockpit_tests.mkdir(parents=True, exist_ok=True)
    (cockpit_tests / "package.json").write_text(
        '{ "name": "cockpit-ui-tests", "scripts": { "test": "vitest run" } }\n',
        encoding="utf-8",
    )
    return repo


class CockpitOverhaulCheckTests(unittest.TestCase):
    def test_passes_on_a_single_shell_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = build_repo(root)
            result = run_check(repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("COCKPIT-OVERHAUL PASS", result.stdout)

    def test_fails_while_the_thin_client_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_repo(Path(tmp))
            (repo / "frontend").mkdir()
            (repo / "frontend" / "package.json").write_text("{}", encoding="utf-8")
            result = run_check(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("frontend/ still exists", result.stderr)

    def test_fails_while_the_nav_group_links_out_to_screens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_repo(Path(tmp))
            result = run_check(repo)  # nav still written with /operations here
            self.assertEqual(result.returncode, 0, result.stderr)

            nav = (
                repo
                / "vendor"
                / "openexecutive"
                / "packages"
                / "ui"
                / "src"
                / "components"
                / "shell"
                / "navConfig.ts"
            )
            nav.write_text(
                'export const NAV_GROUPS = [ { key: "red", label: "RED Operations", items: ['
                '{ href: "/screens/command-center", label: "x" } ] } ];\n',
                encoding="utf-8",
            )
            result = run_check(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("/screens/*", result.stderr)

    def test_fails_when_a_screen_page_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_repo(Path(tmp), pages=len(ROUTES) - 1)
            result = run_check(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(f"/operations/{ROUTES[-1]}", result.stderr)

    def test_fails_while_the_ui_deployment_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_repo(Path(tmp))
            template = repo / "deploy" / "charts" / "redop" / "templates" / "deployment-ui.yaml"
            template.write_text("kind: Deployment\n", encoding="utf-8")
            result = run_check(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("deployment-ui.yaml", result.stderr)

    def test_fails_while_the_ingress_still_routes_screens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_repo(Path(tmp))
            ingress = repo / "deploy" / "charts" / "redop" / "templates" / "ingress.yaml"
            ingress.write_text(
                "paths:\n  - path: /\n  - path: /screens\n", encoding="utf-8"
            )
            result = run_check(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("/screens", result.stderr)

    def test_fails_while_the_section_13_gate_targets_the_retired_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_repo(Path(tmp))
            dod = repo / "scripts" / "check_definition_of_done.sh"
            dod.write_text("./scripts/check_frontend_screens.sh frontend\n", encoding="utf-8")
            result = run_check(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("check_frontend_screens.sh frontend", result.stderr)

    def test_fails_when_the_live_cockpit_does_not_serve_the_ported_screen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_repo(Path(tmp))
            env = dict(os.environ)
            env["REDOP_HEALTH_URL"] = "http://127.0.0.1:9/"
            result = subprocess.run(
                ["bash", str(CHECK), str(repo)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("/operations/command-center", result.stderr)


class _FakeCockpitServer:
    """A one-response HTTP server standing in for the deployed cockpit."""

    def __init__(self, clients_body: str) -> None:
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        body = clients_body.encode("utf-8")
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server API
                if self.path.startswith("/red/clients"):
                    payload, status = body, 200
                else:
                    payload, status = b"<html>RED Operations</html>", 200
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args) -> None:
                return None

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )
        outer._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/"

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


class LiveSeedingCheckTests(unittest.TestCase):
    """The live gate requires a seeded workspace, not an echoed tenant id."""

    def _run(self, body: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_repo(Path(tmp))
            server = _FakeCockpitServer(body)
            try:
                env = dict(os.environ)
                env["REDOP_HEALTH_URL"] = server.url
                return subprocess.run(
                    ["bash", str(CHECK), str(repo)],
                    capture_output=True,
                    text=True,
                    env=env,
                    check=False,
                )
            finally:
                server.stop()

    def test_an_empty_listing_fails_the_seeding_check(self) -> None:
        result = self._run(
            '{"tenant_id":"3fmindset","total":0,"limit":50,"offset":0,'
            '"workspaces":[]}'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not seeded", result.stderr)

    def test_a_seeded_workspace_passes_the_live_check(self) -> None:
        result = self._run(
            '{"tenant_id":"3fmindset","total":1,"limit":50,"offset":0,'
            '"workspaces":[{"workspace_id":"ws-3f","tenant_id":"3fmindset",'
            '"lifecycle":"intake","authorities":[],"children":[]}]}'
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
