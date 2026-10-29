"""Immutable in-memory email template patterns for the pilot catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class EmailTemplateBlock:
    id: str
    purpose: str
    required: bool


@dataclass(frozen=True)
class EmailTemplateDefinition:
    id: str
    version: int
    purpose: str
    review_state: Literal["classified", "needs_review"]
    blocks: tuple[EmailTemplateBlock, ...]


def _block(id: str, purpose: str, required: bool = True) -> EmailTemplateBlock:
    return EmailTemplateBlock(id=id, purpose=purpose, required=required)


EMAIL_TEMPLATES = (
    EmailTemplateDefinition("appointment_confirmation_prep", 1, "Confirm an appointment and help the reader prepare.", "classified", (_block("confirmation", "Confirm the appointment."), _block("preparation", "Explain how to prepare."), _block("next_step", "State what happens next.", False))),
    EmailTemplateDefinition("authority_interview", 1, "Share an expert interview that builds trust and insight.", "classified", (_block("introduction", "Introduce the expert and topic."), _block("interview", "Present the interview."), _block("takeaway", "Highlight a useful takeaway.", False), _block("next_step", "Offer a relevant next step.", False))),
    EmailTemplateDefinition("interview_collection", 1, "Share a collection of interviews and press material.", "classified", (_block("context", "Introduce the collection and its context."), _block("resources", "Present the interviews and press material."), _block("reader_action", "Suggest how to explore or respond to the collection.", False))),
    EmailTemplateDefinition("bonus_with_purchase", 1, "Unclassified example retained for review.", "needs_review", ()),
    EmailTemplateDefinition("cart_recovery", 1, "Help a reader return to an unfinished purchase.", "classified", (_block("reminder", "Recall the unfinished purchase."), _block("benefit", "Reinforce the product value.", False), _block("return_link", "Provide a way to resume the purchase."))),
    EmailTemplateDefinition("resource_roundup", 1, "Share a group of useful resources.", "classified", (_block("introduction", "Set up the resource collection."), _block("resources", "Present the resources."), _block("closing", "Suggest a useful next step.", False))),
    EmailTemplateDefinition("product_faq", 1, "Answer common questions about a product.", "classified", (_block("introduction", "Frame the common questions.", False), _block("questions_and_answers", "Answer product questions."), _block("next_step", "Explain how to learn more or act.", False))),
    EmailTemplateDefinition("time_limited_offer", 1, "Present an offer with a clear time limit.", "classified", (_block("offer", "Describe the offer."), _block("value", "Explain the value."), _block("deadline", "State when the offer ends."), _block("action", "Tell the reader how to act."))),
    EmailTemplateDefinition("strategy_call_invitation", 1, "Invite a reader to book a strategy call.", "classified", (_block("context", "Explain why a call may help."), _block("call_value", "Describe what the call covers."), _block("booking", "Explain how to book."))),
    EmailTemplateDefinition("problem_to_resource", 1, "Connect a reader problem to a helpful resource.", "classified", (_block("problem", "Name the reader's problem."), _block("resource", "Introduce a resource that can help."), _block("action", "Explain how to use the resource."))),
    EmailTemplateDefinition("process_video", 1, "Explain a process through a video.", "classified", (_block("process", "Introduce the process."), _block("video", "Present the video."), _block("next_step", "Suggest what to do next.", False))),
    EmailTemplateDefinition("process_article", 1, "Explain a process through a written guide.", "classified", (_block("process", "Introduce the process."), _block("article", "Present the written guide."), _block("next_step", "Suggest what to do next.", False))),
    EmailTemplateDefinition("results_proof", 1, "Show evidence of results to build confidence.", "classified", (_block("result", "State the result."), _block("evidence", "Show supporting proof."), _block("context", "Explain the result's context.", False), _block("next_step", "Offer a relevant next step.", False))),
    EmailTemplateDefinition("audience_reply_question", 1, "Invite a reader to reply with an answer.", "classified", (_block("question", "Ask a clear question."), _block("reply_request", "Invite a direct reply."), _block("context", "Explain why the answer matters.", False))),
    EmailTemplateDefinition("webinar_attendance_commitment", 1, "Build commitment to attend a webinar.", "classified", (_block("event_details", "Remind the reader of the event."), _block("attendance_value", "Reinforce why attendance matters."), _block("commitment", "Ask the reader to plan to attend."))),
    EmailTemplateDefinition("webinar_early_departure_recovery", 1, "Reconnect with a webinar attendee who left early.", "classified", (_block("acknowledgment", "Acknowledge the early departure."), _block("missed_content", "Share or point to missed material."), _block("next_step", "Offer a way to continue."))),
    EmailTemplateDefinition("webinar_missed_event_recovery", 1, "Reconnect with someone who missed a webinar.", "classified", (_block("acknowledgment", "Acknowledge the missed event."), _block("replay", "Offer access to the replay or key material."), _block("next_step", "Suggest a next step.", False))),
    EmailTemplateDefinition("webinar_offer_recap", 1, "Recap a webinar offer and its next step.", "classified", (_block("recap", "Recall the webinar and its key point."), _block("offer", "Summarize the offer."), _block("action", "Explain how to act."), _block("deadline", "State a deadline.", False))),
    EmailTemplateDefinition("unclassified_email", 1, "Unclassified example retained for review.", "needs_review", ()),
)
