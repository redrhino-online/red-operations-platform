# Email template pilot spec

## Goal

Model the patterns in the 19 `EMAIL EXAMPLES` cards as reusable, in-memory
email template definitions. Document the patterns in the synthesized canon in
the `red-canon` repository.

## User-visible behavior

- The domain package exposes a stable catalog of 19 template definitions.
- Each definition has a stable ID, version, purpose, review state, and ordered
  blocks.
- Each block states its purpose and whether it is required or optional.
- Each of the 18 clear definitions includes its own fill-in email draft. Blanks
  use clear square-bracket labels such as `[FIRST NAME]`.
- Eighteen templates describe distinct email examples that can be inferred from
  the saved card text or images. Each has its own full subject and body draft,
  with slots that fit that example's sequence and purpose.
- The remaining card has cover art, not an email. It has `needs_review` status
  and no fill-in template.
- Definitions contain no source email copy, links, names, or images.
- The canon includes all 18 fill-in templates and explains their purpose.

## Non-goals

- Adding a draft editor, API route, persistence, or template-selection screen.
- Changing stage templates, required asset kinds, or the artifact archive.
- Copying source email text into implementation definitions or new canon prose.
- Guessing the email structure of the cover-art card.
- Adding a rich-text or markdown email editor.
- Expanding the pilot to other board lists.

## Acceptance criteria

1. Given the email-template catalog is imported, when a caller reads it, then it
   returns 19 definitions with unique stable IDs and version values.
2. Given a definition is classifiable, when a caller reads it, then its purpose
   and ordered required or optional blocks describe the inferred structure.
3. Given a definition cannot be classified from the backup, when a caller reads
   it, then its review state is `needs_review` and it does not claim an inferred
   sequence.
4. Given a block list is defined, when the catalog tests run, then every block
   has a unique ID within its template and appears in the intended order.
5. Given a definition is classified, when the catalog is read, then it includes
   a complete subject and body with square-bracket blanks specific to that
   example's intent and order.
6. Given two definitions are classified, when their drafts are compared, then
   each draft is distinct and includes the example-specific steps rather than
   only generic introduction, content, and call-to-action prompts.
7. Given a definition needs review, when the catalog is read, then its body
   template is absent.
8. Given the domain model is added, when existing archive and governance tests
   run, then artifact storage and stage requirements behave as before.
9. Given the canon note is added, when reviewed, then it documents all 18
   distinct fill-in templates in plain words without copying source prose or editing
   `framework-canon/`.

## Constraints

- The pilot covers only the `EMAIL EXAMPLES` list.
- Use the existing archive domain area for the in-memory definitions, but keep
  them separate from archived client artifacts.
- No database, route, or migration changes are needed for this pilot.
- Preserve all unrelated working-tree changes in both repositories.

## Pilot catalog IDs

The catalog uses these stable IDs. The cover-art entry is marked for review.

- `appointment_confirmation_prep`
- `authority_interview`
- `interview_collection`
- `bonus_with_purchase`
- `cart_recovery`
- `resource_roundup`
- `product_faq`
- `time_limited_offer`
- `strategy_call_invitation`
- `problem_to_resource`
- `process_video`
- `process_article`
- `results_proof`
- `audience_reply_question`
- `webinar_attendance_commitment`
- `webinar_early_departure_recovery`
- `webinar_missed_event_recovery`
- `webinar_offer_recap`
- `unclassified_email` (`needs_review`)

## Assumptions and open questions

- ASSUMPTION: “Canon” means synthesized internal documentation in
  `/home/wsl/red-canon/internal/`, not the read-only `framework-canon/` source.
- ASSUMPTION: “Model it in my implementation” means a domain-only definition
  catalog for this pilot. The user selected no API or draft UI.
- ASSUMPTION: The 19-card list contains 18 email examples and one cover-art
  card. The cover-art card remains visible as a review-needed entry without an
  invented email template.
- Open question: None for this pilot. API and UI use can be specified later.

## Ordered plan

1. Extend the email template definitions and catalog in
   `backend/redops/contexts/archive/domain/email_templates.py` with 18 distinct
   subject/body drafts. Verify unique text, sequence-specific slots, and the
   review-needed entry in
   `tests/unit/archive/test_email_templates.py`.
2. Extend `internal/email-template-structures.md` in `red-canon` with the same
   18 fill-in templates and link the source list backup.
3. Run the focused tests and existing archive/governance tests. Review both
   repositories' diffs and ensure unrelated changes remain untouched.

## Rollback

Remove only the new catalog, its focused test, this spec, and the new canon
note. Do not reset either repository or discard other work.
