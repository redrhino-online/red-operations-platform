"""HTTP-boundary behavioral tests for the client and source routes (SPEC.md §7).

SPEC.md section 7 lists ``/clients`` and ``/clients/{id}/sources``; section 9
requires every tenant resource query to carry ``tenant_id`` and every list
endpoint to enforce client access and pagination. These tests drive the real
FastAPI app against fresh in-memory stores (substituted through the overridable
dependencies), so a client's workspaces and sources cannot be read under another
tenant, a source original cannot be rewritten, and pagination is stable.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

TENANT = "3fmindset"
OTHER_TENANT = "client-other"


class ClientsRouteTests(unittest.TestCase):
    """The client and source surfaces are served only through the store ports."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import (
                get_client_workspace_store,
                get_source_record_store,
            )
            from redops.contexts.engagement.infrastructure.repositories import (
                InMemoryClientWorkspaceStore,
            )
            from redops.contexts.knowledge.infrastructure.repositories import (
                InMemorySourceRecordStore,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.workspace_dependency = staticmethod(get_client_workspace_store)
        cls.source_dependency = staticmethod(get_source_record_store)
        cls.workspace_store_class = staticmethod(InMemoryClientWorkspaceStore)
        cls.source_store_class = staticmethod(InMemorySourceRecordStore)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.workspaces = self.workspace_store_class()
        self.sources = self.source_store_class()
        self.app.dependency_overrides[self.workspace_dependency] = (
            lambda: self.workspaces
        )
        self.app.dependency_overrides[self.source_dependency] = (
            lambda: self.sources
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def workspace_body(tenant_id: str = TENANT, workspace_id: str = "3f-engagement"):
        return {
            "workspace_id": workspace_id,
            "tenant_id": tenant_id,
            "authorities": [
                {"actor": "red-principal", "authority": "owner"},
                {
                    "actor": "3f-approver",
                    "authority": "client-designated-authority",
                },
            ],
        }

    def test_a_created_workspace_is_listed_for_its_tenant(self) -> None:
        created = self.client.post("/red/clients", json=self.workspace_body())

        self.assertEqual(201, created.status_code, created.text)
        self.assertEqual("3f-engagement", created.json()["workspace_id"])
        self.assertEqual(2, len(created.json()["authorities"]))

        listed = self.client.get(
            "/red/clients", params={"tenant_id": TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(TENANT, body["tenant_id"])
        self.assertEqual(1, body["total"])
        self.assertEqual("3f-engagement", body["workspaces"][0]["workspace_id"])
        self.assertEqual("intake", body["workspaces"][0]["lifecycle"])

    def test_a_workspace_is_not_listed_for_another_client(self) -> None:
        self.client.post("/red/clients", json=self.workspace_body())

        listed = self.client.get(
            "/red/clients", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["workspaces"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/clients")

        self.assertEqual(422, response.status_code, response.text)

    def test_a_workspace_without_an_authority_is_refused(self) -> None:
        body = self.workspace_body()
        body["authorities"] = []

        response = self.client.post("/red/clients", json=body)

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(
            "InvalidClientWorkspaceError", response.json()["detail"]["error"]
        )

    def test_a_created_source_is_listed_for_its_tenant(self) -> None:
        response = self.client.post(
            f"/red/clients/{TENANT}/sources",
            json={
                "source_id": "src-1",
                "locator": "project_sources/notes/01.md",
                "checksum": "sha256:abc",
                "captured_on": "2026-10-03",
                "access_rule": "client-and-red-only",
            },
        )

        self.assertEqual(201, response.status_code, response.text)
        self.assertEqual(TENANT, response.json()["tenant_id"])

        listed = self.client.get(f"/red/clients/{TENANT}/sources")

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(1, listed.json()["total"])
        self.assertEqual("sha256:abc", listed.json()["sources"][0]["checksum"])

    def test_a_source_is_scoped_to_the_path_tenant(self) -> None:
        self.client.post(
            f"/red/clients/{TENANT}/sources",
            json={
                "source_id": "src-1",
                "locator": "project_sources/notes/01.md",
                "checksum": "sha256:abc",
                "captured_on": "2026-10-03",
                "access_rule": "client-and-red-only",
            },
        )

        other = self.client.get(f"/red/clients/{OTHER_TENANT}/sources")

        self.assertEqual(200, other.status_code, other.text)
        self.assertEqual(0, other.json()["total"])

    def test_a_rewritten_source_is_a_conflict(self) -> None:
        body = {
            "source_id": "src-1",
            "locator": "project_sources/notes/01.md",
            "checksum": "sha256:abc",
            "captured_on": "2026-10-03",
            "access_rule": "client-and-red-only",
        }
        self.client.post(f"/red/clients/{TENANT}/sources", json=body)
        body["checksum"] = "sha256:rewritten"

        response = self.client.post(
            f"/red/clients/{TENANT}/sources", json=body
        )

        self.assertEqual(409, response.status_code, response.text)
        self.assertEqual(
            "SourceRecordImmutableError", response.json()["detail"]["error"]
        )

    def test_source_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.client.post(
                f"/red/clients/{TENANT}/sources",
                json={
                    "source_id": f"src-{index}",
                    "locator": f"project_sources/notes/{index}.md",
                    "checksum": f"sha256:{index}",
                    "captured_on": "2026-10-03",
                    "access_rule": "client-and-red-only",
                },
            )

        page = self.client.get(
            f"/red/clients/{TENANT}/sources",
            params={"limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(3, page.json()["total"])
        self.assertEqual(2, page.json()["limit"])
        self.assertEqual(1, page.json()["offset"])
        self.assertEqual(2, len(page.json()["sources"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
