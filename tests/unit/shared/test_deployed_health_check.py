"""Behavioral tests for the condition 9 deployed-RED health gate.

SPEC.md section 13 condition 9 requires the prototype to be deployed on the
Atlas k3s cluster with a passing deployed health check. The host once served the
OpenExecutive shell while ``make done`` still passed on a bare HTTP 200, so this
gate requires a RED identity marker. These tests run
``scripts/check_deployed_red_health.sh`` against a local stub server: a RED body
passes, and an OpenExecutive or other body fails rather than certifying the
wrong app.
"""

from __future__ import annotations

import http.server
import os
import subprocess
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "check_deployed_red_health.sh"

RED_BODY = "<title>RED Operations Platform</title><h1>RED Operations Director</h1>"
OPENEXECUTIVE_BODY = "<title>Open Executive</title><h1>OpenExecutive</h1>"


class _Handler(http.server.BaseHTTPRequestHandler):
    body = RED_BODY
    status = 200

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        payload = self.body.encode("utf-8")
        self.send_response(self.status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:  # keep the test output quiet
        return


@contextmanager
def serve(body: str, status: int = 200) -> Iterator[str]:
    handler = type("Handler", (_Handler,), {"body": body, "status": status})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run(url: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, REDOP_HEALTH_INSECURE="0")
    return subprocess.run(
        ["bash", str(SCRIPT), url],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


class DeployedRedHealthCheckTest(unittest.TestCase):
    def test_red_body_passes(self) -> None:
        with serve(RED_BODY) as url:
            result = run(url)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RED Operations", result.stdout)

    def test_openexecutive_body_fails(self) -> None:
        with serve(OPENEXECUTIVE_BODY) as url:
            result = run(url)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not RED", result.stderr)

    def test_missing_marker_fails(self) -> None:
        with serve("<title>Some other app</title>") as url:
            result = run(url)

        self.assertNotEqual(result.returncode, 0)

    def test_http_error_fails(self) -> None:
        with serve(RED_BODY, status=500) as url:
            result = run(url)

        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
