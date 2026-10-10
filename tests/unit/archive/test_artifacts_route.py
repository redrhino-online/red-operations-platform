"""HTTP-boundary behavioral tests for the stage artifact archive routes.

docs/specs/stage-artifact-archive.md sections 1.3 and 4 (acceptance criteria A1
and A2): the archive is the collection and archiving source for every artifact
of every stage, the path tenant is the authoritative client scope, the
workspace is resolved through the engagement store, omitted asset id, version
and drop date take their defaults, an identical replay is idempotent, a
different same-key body is a named 409, and the list is tenant scoped,
filterable, paginated and carries the full markdown.

These tests drive the real FastAPI app against fresh in-memory stores
substituted through the overridable dependencies, so the archive is read only
under its own tenant and never written through the surface.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest
from datetime import date

TENANT = "client-3f"
OTHER_TENANT = "client-other"
WORKSPACE = "ws-3f"
OTHER_WORKSPACE = "ws-other"
MARKDOWN = "Demo: signed scope\n\n## Scope\n\n- item one\n"


def artifact_body(**overrides):
    body = {
        "workspace_id": WORKSPACE,
        "stage_number": 0,
        "kind": "signed-scope",
        "markdown": MARKDOWN,
        "owner": "red-principal",
    }
    body.update(overrides)
    return body


class StageArtifactsRouteTests(unittest.TestCase):
    """The archive surface drops and lists artifacts under the path tenant."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import (
                get_client_workspace_store,
                get_stage_artifact_store,
            )
            from redops.contexts.archive.infrastructure.repositories import (
                InMemoryStageArtifactStore,
            )
            from redops.contexts.engagement.infrastructure.repositories import (
                InMemoryClientWorkspaceStore,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.artifact_dependency = staticmethod(get_stage_artifact_store)
        cls.workspace_dependency = staticmethod(get_client_workspace_store)
        cls.artifact_store_class = staticmethod(InMemoryStageArtifactStore)
        cls.workspace_store_class = staticmethod(InMemoryClientWorkspaceStore)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.artifacts = self.artifact_store_class()
        self.workspaces = self.workspace_store_class()
        self.app.dependency_overrides[self.artifact_dependency] = (
            lambda: self.artifacts
        )
        self.app.dependency_overrides[self.workspace_dependency] = (
            lambda: self.workspaces
        )
        self.client = self.test_client(self.app)
        self.register_workspace(TENANT)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def register_workspace(
        self, tenant_id: str, workspace_id: str = WORKSPACE
    ) -> None:
        response = self.client.post(
            "/red/clients",
            json={
                "workspace_id": workspace_id,
                "tenant_id": tenant_id,
                "authorities": [
                    {
                        "actor": "red-principal",
                        "authority": "production-owner",
                    },
                ],
            },
        )
        self.assertEqual(201, response.status_code, response.text)

    def drop(self, tenant_id: str = TENANT, **overrides):
        return self.client.post(
            f"/red/clients/{tenant_id}/artifacts",
            json=artifact_body(**overrides),
        )

    # -- A1: the drop route -------------------------------------------------

    def test_a_dropped_artifact_is_created_with_its_defaults(self) -> None:
        response = self.drop()

        self.assertEqual(201, response.status_code, response.text)
        artifact = response.json()
        self.assertEqual(TENANT, artifact["tenant_id"])
        self.assertEqual(WORKSPACE, artifact["workspace_id"])
        self.assertEqual(0, artifact["stage_number"])
        self.assertEqual("signed-scope", artifact["kind"])
        self.assertEqual("signed-scope", artifact["asset_id"])
        self.assertEqual(1, artifact["version"])
        self.assertEqual(MARKDOWN, artifact["markdown"])
        self.assertEqual("red-principal", artifact["owner"])
        self.assertIsNone(artifact["note"])
        self.assertEqual(date.today().isoformat(), artifact["dropped_on"])

    def test_an_explicit_asset_id_version_note_and_date_are_kept(self) -> None:
        response = self.drop(
            asset_id="scope-acme",
            version=3,
            note="Demo: captured at intake",
            dropped_on="2026-10-01",
        )

        self.assertEqual(201, response.status_code, response.text)
        artifact = response.json()
        self.assertEqual("scope-acme", artifact["asset_id"])
        self.assertEqual(3, artifact["version"])
        self.assertEqual("Demo: captured at intake", artifact["note"])
        self.assertEqual("2026-10-01", artifact["dropped_on"])

    def test_the_next_drop_of_the_same_asset_takes_the_next_free_version(
        self,
    ) -> None:
        first = self.drop()
        second = self.drop(markdown="Demo: revised scope")

        self.assertEqual(201, first.status_code, first.text)
        self.assertEqual(201, second.status_code, second.text)
        self.assertEqual(1, first.json()["version"])
        self.assertEqual(2, second.json()["version"])

    def test_an_identical_replay_succeeds_idempotently(self) -> None:
        # An identical replay re-states the same key, so the version must be
        # explicit; a replay without one drops the next version instead.
        first = self.drop()
        replay = self.drop(version=1)

        self.assertEqual(201, first.status_code, first.text)
        self.assertEqual(201, replay.status_code, replay.text)
        self.assertEqual(first.json(), replay.json())

        listed = self.client.get(f"/red/clients/{TENANT}/artifacts")
        self.assertEqual(1, listed.json()["total"], listed.text)

    def test_a_different_body_under_the_same_key_is_a_named_409(self) -> None:
        self.drop()

        conflict = self.drop(version=1, markdown="Demo: rewritten scope")

        self.assertEqual(409, conflict.status_code, conflict.text)
        self.assertEqual(
            "StageArtifactVersionConflictError",
            conflict.json()["detail"]["error"],
        )

    def test_an_unknown_workspace_is_a_404(self) -> None:
        response = self.drop(workspace_id="ws-unknown")

        self.assertEqual(404, response.status_code, response.text)
        self.assertEqual(
            "ClientWorkspaceNotFoundError",
            response.json()["detail"]["error"],
        )

    def test_a_workspace_of_another_tenant_is_a_404(self) -> None:
        self.register_workspace(OTHER_TENANT, OTHER_WORKSPACE)

        response = self.drop(workspace_id=OTHER_WORKSPACE)

        self.assertEqual(404, response.status_code, response.text)

    def test_a_blank_field_is_a_named_422(self) -> None:
        # A blank workspace is refused earlier, at the workspace resolution
        # (a blank workspace is an unknown workspace), so the domain blank
        # refusal covers the artifact's own content fields.
        for field in ("kind", "markdown", "owner"):
            with self.subTest(field=field):
                response = self.drop(**{field: "   "})

                self.assertEqual(422, response.status_code, response.text)
                self.assertEqual(
                    "BlankArtifactFieldError",
                    response.json()["detail"]["error"],
                )

    def test_a_blank_workspace_is_an_unknown_workspace(self) -> None:
        response = self.drop(workspace_id="   ")

        self.assertEqual(404, response.status_code, response.text)
        self.assertEqual(
            "ClientWorkspaceNotFoundError",
            response.json()["detail"]["error"],
        )

    def test_a_stage_outside_the_pipeline_is_a_named_422(self) -> None:
        for stage_number in (-1, 11):
            with self.subTest(stage_number=stage_number):
                response = self.drop(stage_number=stage_number)

                self.assertEqual(422, response.status_code, response.text)
                self.assertEqual(
                    "InvalidArtifactStageError",
                    response.json()["detail"]["error"],
                )

    def test_a_non_positive_version_is_a_named_422(self) -> None:
        response = self.drop(version=0)

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(
            "InvalidArtifactVersionError",
            response.json()["detail"]["error"],
        )

    def test_a_body_tenant_cannot_override_the_path_tenant(self) -> None:
        response = self.client.post(
            f"/red/clients/{TENANT}/artifacts",
            json={**artifact_body(), "tenant_id": OTHER_TENANT},
        )

        self.assertEqual(201, response.status_code, response.text)
        self.assertEqual(TENANT, response.json()["tenant_id"])

        other = self.client.get(f"/red/clients/{OTHER_TENANT}/artifacts")
        self.assertEqual(0, other.json()["total"], other.text)

    # -- A2: the list route -------------------------------------------------

    def test_the_list_is_tenant_scoped(self) -> None:
        self.drop()
        self.register_workspace(OTHER_TENANT)
        other_drop = self.client.post(
            f"/red/clients/{OTHER_TENANT}/artifacts",
            json=artifact_body(markdown="Demo: other client's scope"),
        )
        self.assertEqual(201, other_drop.status_code, other_drop.text)

        own = self.client.get(f"/red/clients/{TENANT}/artifacts")
        other = self.client.get(f"/red/clients/{OTHER_TENANT}/artifacts")

        self.assertEqual(200, own.status_code, own.text)
        self.assertEqual(1, own.json()["total"])
        self.assertTrue(
            all(item["tenant_id"] == TENANT for item in own.json()["artifacts"])
        )
        self.assertEqual(200, other.status_code, other.text)
        self.assertEqual(1, other.json()["total"])
        self.assertTrue(
            all(
                item["tenant_id"] == OTHER_TENANT
                for item in other.json()["artifacts"]
            )
        )

    def test_the_list_includes_the_full_markdown(self) -> None:
        self.drop()

        listed = self.client.get(f"/red/clients/{TENANT}/artifacts")

        self.assertEqual(MARKDOWN, listed.json()["artifacts"][0]["markdown"])

    def test_the_list_applies_the_optional_filters(self) -> None:
        self.register_workspace(TENANT, OTHER_WORKSPACE)
        self.drop()
        self.drop(version=2)
        self.drop(
            workspace_id=OTHER_WORKSPACE,
            kind="intake-questionnaire",
            markdown="Demo: intake questionnaire",
        )
        self.drop(
            stage_number=1,
            kind="avatar-profile",
            markdown="Demo: avatar profile",
        )

        by_workspace = self.client.get(
            f"/red/clients/{TENANT}/artifacts",
            params={"workspace_id": OTHER_WORKSPACE},
        )
        self.assertEqual(1, by_workspace.json()["total"])
        self.assertEqual(
            "intake-questionnaire", by_workspace.json()["artifacts"][0]["kind"]
        )

        by_stage = self.client.get(
            f"/red/clients/{TENANT}/artifacts", params={"stage_number": 1}
        )
        self.assertEqual(1, by_stage.json()["total"])
        self.assertEqual("avatar-profile", by_stage.json()["artifacts"][0]["kind"])

        by_kind = self.client.get(
            f"/red/clients/{TENANT}/artifacts", params={"kind": "signed-scope"}
        )
        self.assertEqual(2, by_kind.json()["total"])

        by_asset = self.client.get(
            f"/red/clients/{TENANT}/artifacts",
            params={"asset_id": "signed-scope"},
        )
        self.assertEqual(2, by_asset.json()["total"])
        self.assertEqual(
            [2, 1],
            [item["version"] for item in by_asset.json()["artifacts"]],
        )

        combined = self.client.get(
            f"/red/clients/{TENANT}/artifacts",
            params={
                "workspace_id": WORKSPACE,
                "stage_number": 0,
                "kind": "signed-scope",
                "asset_id": "signed-scope",
            },
        )
        self.assertEqual(
            [2, 1],
            [item["version"] for item in combined.json()["artifacts"]],
        )

    def test_the_list_is_sorted_by_stage_kind_asset_and_newest_version(
        self,
    ) -> None:
        self.drop(kind="intake-questionnaire", markdown="Demo: intake")
        self.drop(version=2)
        self.drop(version=1)
        self.drop(
            stage_number=1,
            kind="avatar-profile",
            markdown="Demo: avatar",
        )

        listed = self.client.get(f"/red/clients/{TENANT}/artifacts")

        self.assertEqual(
            [
                (0, "intake-questionnaire", 1),
                (0, "signed-scope", 2),
                (0, "signed-scope", 1),
                (1, "avatar-profile", 1),
            ],
            [
                (item["stage_number"], item["kind"], item["version"])
                for item in listed.json()["artifacts"]
            ],
        )

    def test_pagination_is_applied_after_tenant_scoping(self) -> None:
        for version in (1, 2, 3):
            self.drop(version=version)

        page = self.client.get(
            f"/red/clients/{TENANT}/artifacts",
            params={"limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(3, page.json()["total"])
        self.assertEqual(2, page.json()["limit"])
        self.assertEqual(1, page.json()["offset"])
        self.assertEqual(
            [2, 1],
            [item["version"] for item in page.json()["artifacts"]],
        )

    def test_the_page_bounds_are_enforced(self) -> None:
        for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
            with self.subTest(params=params):
                response = self.client.get(
                    f"/red/clients/{TENANT}/artifacts", params=params
                )

                self.assertEqual(422, response.status_code, response.text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
