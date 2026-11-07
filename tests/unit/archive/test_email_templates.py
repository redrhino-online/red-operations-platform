from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
import re

from redops.contexts.archive.domain.email_templates import EMAIL_TEMPLATES


EXPECTED_CLASSIFIED_BLOCK_IDS = {
    "appointment_confirmation_prep": ("confirmation", "purpose", "preparation", "value", "close"),
    "authority_interview": ("topic", "interview", "introduction", "resources"),
    "interview_collection": ("value", "sections", "collection_link", "entries", "share", "community"),
    "bonus_with_purchase": ("bonus", "claim", "assets", "benefits", "learn_more", "close"),
    "cart_recovery": ("reminder", "support", "value", "checkout", "close"),
    "resource_roundup": ("context", "resources", "implementation", "support"),
    "product_faq": ("questions", "qualification", "booking", "conditions"),
    "time_limited_offer": ("discount", "reasons", "price_access", "video", "refund_terms", "benefits", "value_stack", "repeated_action", "deadline_support"),
    "strategy_call_invitation": ("session", "booking", "reason", "follow_on", "reassurance", "preparation", "qualification", "repeat_booking"),
    "problem_to_resource": ("problem", "video", "feedback", "invitation"),
    "process_video": ("template", "diagram", "stages", "application"),
    "process_article": ("problem", "article", "application", "personal_note", "related_offer"),
    "results_proof": ("walkthrough", "metrics", "interpretation", "fit"),
    "audience_reply_question": ("question", "reply", "use"),
    "webinar_attendance_commitment": ("confirmation", "commitment", "quality", "preparedness", "engagement"),
    "webinar_early_departure_recovery": ("technical_check", "replay", "controls", "proof"),
    "webinar_missed_event_recovery": ("acknowledgment", "value", "replay", "reassurance"),
    "webinar_offer_recap": ("thanks", "offer", "items", "total", "action", "questions"),
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
        self.assertEqual({"unclassified_email"}, review_needed)
        for template in EMAIL_TEMPLATES:
            if template.review_state == "needs_review":
                self.assertEqual((), template.blocks)
                self.assertIsNone(template.body_template)

    def test_all_classified_templates_have_distinct_subject_and_complete_body(self) -> None:
        classified = [template for template in EMAIL_TEMPLATES if template.review_state == "classified"]
        self.assertEqual(18, len(classified))
        subjects = []
        for template in classified:
            with self.subTest(template=template.id):
                self.assertIsNotNone(template.body_template)
                subject, separator, body = template.body_template.partition("\n\n")
                self.assertTrue(separator)
                self.assertTrue(subject.startswith("Subject: "))
                self.assertGreater(len(body.split()), 60)
                self.assertTrue(re.search(r"\[([A-Z][A-Z0-9 ]+)\]", body))
                subjects.append(subject)
        self.assertEqual(len(subjects), len(set(subjects)))

    def test_definitions_are_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            EMAIL_TEMPLATES[0].version = 2


if __name__ == "__main__":
    unittest.main()
