"""HTTP-boundary behavioral tests for the approved method route (SPEC.md §7).

SPEC.md section 7 lists ``/methods``; section 9 requires every query to carry the
client scope; section 3 pins an exact version and intended use at approval and
section 4 keeps the approved version identifiable. These tests drive the real
FastAPI app against a fresh in-memory approved-method store (substituted through
the overridable dependency), so a client's approved methods are readable for that
tenant, are unreadable for another, and cannot be written through the read
surface (a direct write would confer the approval governance owns).

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date

from redops.contexts.method.domain.value_objects import (
    MethodApproval,
    SemanticVersion,
)

from .test_method_version import method_version

TENANT = "client-3f"
OTHER_TENANT = "client-other"
ON = date(2026, 10, 2)


def approved_method():
    return method_version().approve(
        approved_by="client-approver-1",
        intended_use="3f pilot campaign",
        on=ON,
    )


class MethodsRouteTests(unittest.TestCase):
    """The method surface is a tenant-scoped read over the approved-method store."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import get_method_version_repository
            from redops.contexts.method.infrastructure.repositories import (
                InMemoryMethodVersionRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.method_dependency = staticmethod(get_method_version_repository)
        cls.repository_class = staticmethod(InMemoryMethodVersionRepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.methods = self.repository_class()
        self.app.dependency_overrides[self.method_dependency] = lambda: self.methods
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_an_approved_method_is_listed_for_its_tenant(self) -> None:
        self.methods.save(approved_method())

        listed = self.client.get("/red/methods", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        method = body["methods"][0]
        self.assertEqual("method-3f", method["method_id"])
        self.assertEqual("1.0.0", method["semantic_version"])
        self.assertTrue(method["is_approved"])
        self.assertEqual("client-approver-1", method["approved_by"])
        self.assertEqual("3f pilot campaign", method["intended_use"])
        self.assertEqual("qualified referrals", method["primary_currency"])
        self.assertIsNotNone(method["signature_solution_id"])

    def test_the_pinned_signature_solution_is_projected_for_the_map(self) -> None:
        self.methods.save(approved_method())

        listed = self.client.get("/red/methods", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        solution = listed.json()["methods"][0]["signature_solution"]
        self.assertEqual("solution-3f", solution["solution_id"])
        self.assertEqual(
            "from chaotic delivery to a launched campaign",
            solution["transformation_map"],
        )
        self.assertEqual("chaotic", solution["starting_state"])
        self.assertEqual("launched", solution["final_state"])
        self.assertEqual(3, len(solution["phases"]))
        steps = [step for phase in solution["phases"] for step in phase["steps"]]
        self.assertEqual(9, len(steps))
        self.assertEqual("step-1", steps[0]["step_id"])
        self.assertEqual("diagnosed", steps[0]["final_state"])
        self.assertEqual(["Diagnose inputs"], steps[0]["inputs"])
        self.assertEqual(["Diagnose actions"], steps[0]["actions"])
        self.assertEqual(["Diagnose outputs"], steps[0]["outputs"])

    def test_the_pinned_primary_currency_is_projected_in_full(self) -> None:
        self.methods.save(approved_method())

        listed = self.client.get("/red/methods", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        method = listed.json()["methods"][0]
        self.assertEqual("qualified referrals", method["primary_currency"])
        detail = method["primary_currency_detail"]
        self.assertEqual("client-3f", detail["tenant_id"])
        self.assertEqual("qualified referrals", detail["currency"])
        self.assertEqual(
            "owner-operators of two to five person service firms",
            detail["audience"],
        )
        self.assertEqual(
            "4 qualified referrals per month", detail["current_measure"]
        )
        self.assertEqual(
            "12 qualified referrals per month", detail["desired_measure"]
        )
        self.assertEqual("referral partner network", detail["mechanism"])

    def test_the_pinned_diagnostic_model_is_projected_in_full(self) -> None:
        self.methods.save(approved_method())

        listed = self.client.get("/red/methods", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        method = listed.json()["methods"][0]
        self.assertEqual("model-3f", method["diagnostic_model_id"])
        model = method["diagnostic_model"]
        self.assertEqual("model-3f", model["model_id"])
        self.assertEqual("client-3f", model["tenant_id"])
        self.assertEqual("Growth Pyramid", model["name"])
        self.assertEqual(
            "climb from Stuck to Scaling by installing the referral network",
            model["progression"],
        )
        self.assertEqual(
            "rank the prospect by observable monthly referral count",
            model["qualification_logic"],
        )
        self.assertEqual(
            "asset://diagnostic/3f-growth-pyramid.png", model["visual"]
        )
        self.assertEqual(
            "Four levels from Stuck to Scaling, each placed by observable "
            "monthly referral count",
            model["explanatory_copy"],
        )
        levels = model["levels"]
        self.assertEqual(2, len(levels))
        self.assertEqual("level-1", levels[0]["level_id"])
        self.assertEqual("Stuck", levels[0]["name"])
        self.assertEqual(
            ["under 4 qualified referrals per month"],
            levels[0]["observable_measures"],
        )
        self.assertEqual(["Stuck symptoms"], levels[0]["symptoms"])
        self.assertEqual(["Stuck behaviors"], levels[0]["behaviors"])
        self.assertEqual(["Stuck problems"], levels[0]["problems"])
        self.assertEqual("level-2", levels[1]["level_id"])
        self.assertEqual(
            ["12 or more qualified referrals per month"],
            levels[1]["observable_measures"],
        )

    def test_a_method_without_the_stage_2_and_3_assets_projects_them_as_none(
        self,
    ) -> None:
        bare = replace(
            method_version(),
            approval=MethodApproval(
                version=SemanticVersion(1, 0, 0),
                intended_use="3f pilot campaign",
                approved_by="client-approver-1",
                approved_on=ON,
            ),
            primary_currency=None,
            diagnostic_model=None,
        )
        self.methods.save(bare)

        listed = self.client.get("/red/methods", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        method = listed.json()["methods"][0]
        self.assertIsNone(method["primary_currency"])
        self.assertIsNone(method["primary_currency_detail"])
        self.assertIsNone(method["diagnostic_model_id"])
        self.assertIsNone(method["diagnostic_model"])

    def test_a_method_is_not_listed_for_another_client(self) -> None:
        self.methods.save(approved_method())

        listed = self.client.get(
            "/red/methods", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["methods"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/methods")

        self.assertEqual(422, response.status_code, response.text)

    def test_the_read_surface_refuses_a_write(self) -> None:
        response = self.client.post("/red/methods", json={"method_id": "method-3f"})

        self.assertEqual(405, response.status_code, response.text)

    def test_method_pagination_is_applied_after_tenant_scoping(self) -> None:
        self.methods.save(approved_method())
        second = method_version(method_id="a-method").approve(
            approved_by="client-approver-1",
            intended_use="3f pilot campaign",
            on=ON,
        )
        self.methods.save(second)

        page = self.client.get(
            "/red/methods",
            params={"tenant_id": TENANT, "limit": 1, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(2, page.json()["total"])
        self.assertEqual(1, len(page.json()["methods"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
