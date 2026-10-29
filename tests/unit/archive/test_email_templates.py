from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.archive.domain.email_templates import EMAIL_TEMPLATES


EXPECTED_CLASSIFIED_BLOCK_IDS = {
    "appointment_confirmation_prep": ("confirmation", "preparation", "next_step"),
    "authority_interview": ("introduction", "interview", "takeaway", "next_step"),
    "interview_collection": ("context", "resources", "reader_action"),
    "cart_recovery": ("reminder", "benefit", "return_link"),
    "resource_roundup": ("introduction", "resources", "closing"),
    "product_faq": ("introduction", "questions_and_answers", "next_step"),
    "time_limited_offer": ("offer", "value", "deadline", "action"),
    "strategy_call_invitation": ("context", "call_value", "booking"),
    "problem_to_resource": ("problem", "resource", "action"),
    "process_video": ("process", "video", "next_step"),
    "process_article": ("process", "article", "next_step"),
    "results_proof": ("result", "evidence", "context", "next_step"),
    "audience_reply_question": ("question", "reply_request", "context"),
    "webinar_attendance_commitment": ("event_details", "attendance_value", "commitment"),
    "webinar_early_departure_recovery": ("acknowledgment", "missed_content", "next_step"),
    "webinar_missed_event_recovery": ("acknowledgment", "replay", "next_step"),
    "webinar_offer_recap": ("recap", "offer", "action", "deadline"),
}


class EmailTemplateCatalogTests(unittest.TestCase):
    def test_catalog_has_nineteen_unique_stable_ids_and_versions(self) -> None:
        self.assertEqual(19, len(EMAIL_TEMPLATES))
        ids = [template.id for template in EMAIL_TEMPLATES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(template.id and template.version >= 1 for template in EMAIL_TEMPLATES))

    def test_classified_entries_have_meaningful_purposes_and_ordered_blocks(self) -> None:
        for template in EMAIL_TEMPLATES:
            with self.subTest(template=template.id):
                self.assertGreater(len(template.purpose.strip()), 12)
                if template.review_state == "classified":
                    self.assertTrue(template.blocks)
                    block_ids = [block.id for block in template.blocks]
                    self.assertEqual(len(block_ids), len(set(block_ids)))
                    self.assertEqual(len(block_ids), len(template.blocks))
                    self.assertTrue(all(block.purpose.strip() for block in template.blocks))

    def test_classified_block_ids_match_expected_order(self) -> None:
        classified = {
            template.id: tuple(block.id for block in template.blocks)
            for template in EMAIL_TEMPLATES
            if template.review_state == "classified"
        }
        self.assertEqual(EXPECTED_CLASSIFIED_BLOCK_IDS, classified)

    def test_review_needed_entries_have_no_inferred_blocks(self) -> None:
        review_needed = {template.id for template in EMAIL_TEMPLATES if template.review_state == "needs_review"}
        self.assertEqual({"bonus_with_purchase", "unclassified_email"}, review_needed)
        for template in EMAIL_TEMPLATES:
            if template.review_state == "needs_review":
                self.assertEqual((), template.blocks)

    def test_definitions_are_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            EMAIL_TEMPLATES[0].version = 2


if __name__ == "__main__":
    unittest.main()
