"""HTTP-boundary behavioral tests for the stage gate schema route (spec §4.2).

The schema-driven record-gate form is built from ``GET
/red/stages/{n}/gate-schema``, which returns the JSON Schema of the exact
``RecordStageNGateRequest`` model the ``POST
/red/clients/{tenant_id}/stages/{n}/gate`` route accepts. These tests prove the
schema and the route body cannot drift: for every canonical stage the returned
schema is the request model's own ``model_json_schema()``, its properties are
exactly the model's fields, and the stage's ``seed.py`` payload -- the fixture
the cockpit assembles the form from -- validates against the model. An unknown
stage number is a named 404.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest


class StageGateSchemaRouteTests(unittest.TestCase):
    """Every canonical stage exposes the schema of its own gate request body."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops import seed
            from redops.api.app import create_app
            from redops.api.schemas import (
                RecordStageEightGateRequest,
                RecordStageFiveGateRequest,
                RecordStageFourGateRequest,
                RecordStageNineGateRequest,
                RecordStageOneGateRequest,
                RecordStageSevenGateRequest,
                RecordStageSixGateRequest,
                RecordStageTenGateRequest,
                RecordStageThreeGateRequest,
                RecordStageTwoGateRequest,
                RecordStageZeroGateRequest,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.models = (
            RecordStageZeroGateRequest,
            RecordStageOneGateRequest,
            RecordStageTwoGateRequest,
            RecordStageThreeGateRequest,
            RecordStageFourGateRequest,
            RecordStageFiveGateRequest,
            RecordStageSixGateRequest,
            RecordStageSevenGateRequest,
            RecordStageEightGateRequest,
            RecordStageNineGateRequest,
            RecordStageTenGateRequest,
        )
        cls.payloads = (
            seed.stage_zero_payload(),
            seed.stage_one_payload(),
            seed.stage_two_payload(),
            seed.stage_three_payload(),
            seed.stage_four_payload(),
            seed.stage_five_payload(),
            seed.stage_six_payload(),
            seed.stage_seven_payload(),
            seed.stage_eight_payload(),
            seed.stage_nine_payload(),
            seed.stage_ten_payload(),
        )

    def setUp(self) -> None:
        self.app = self.create_app()
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_every_canonical_stage_returns_its_request_schema(self) -> None:
        for stage_number, model in enumerate(self.models):
            with self.subTest(stage_number=stage_number):
                response = self.client.get(
                    f"/red/stages/{stage_number}/gate-schema"
                )

                self.assertEqual(200, response.status_code, response.text)
                self.assertEqual(model.model_json_schema(), response.json())

    def test_the_seed_payload_of_every_stage_validates_against_its_schema(
        self,
    ) -> None:
        for stage_number, (model, payload) in enumerate(
            zip(self.models, self.payloads)
        ):
            with self.subTest(stage_number=stage_number):
                response = self.client.get(
                    f"/red/stages/{stage_number}/gate-schema"
                )

                self.assertEqual(200, response.status_code, response.text)
                schema = response.json()
                self.assertEqual(
                    set(model.model_fields), set(schema["properties"])
                )
                self.assertLessEqual(set(payload), set(model.model_fields))
                self.assertIsNotNone(model.model_validate(payload))

    def test_every_internal_ref_resolves_inside_the_returned_schema(self) -> None:
        """Internal ``$defs`` are allowed; the form resolves them in document."""

        def refs(node: object) -> set[str]:
            found: set[str] = set()
            if isinstance(node, dict):
                if "$ref" in node and isinstance(node["$ref"], str):
                    found.add(node["$ref"])
                for value in node.values():
                    found |= refs(value)
            elif isinstance(node, list):
                for value in node:
                    found |= refs(value)
            return found

        for stage_number in range(len(self.models)):
            with self.subTest(stage_number=stage_number):
                response = self.client.get(
                    f"/red/stages/{stage_number}/gate-schema"
                )

                self.assertEqual(200, response.status_code, response.text)
                schema = response.json()
                definitions = set(schema.get("$defs", {}))
                for reference in refs(schema):
                    self.assertEqual("#/$defs/", reference[:8])
                    self.assertIn(
                        reference[len("#/$defs/") :],
                        definitions,
                        schema,
                    )

    def test_an_unknown_stage_is_a_named_404(self) -> None:
        for stage_number in (-1, 11, 42):
            with self.subTest(stage_number=stage_number):
                response = self.client.get(
                    f"/red/stages/{stage_number}/gate-schema"
                )

                self.assertEqual(404, response.status_code, response.text)
                self.assertEqual(
                    "UnknownStageError", response.json()["detail"]["error"]
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
