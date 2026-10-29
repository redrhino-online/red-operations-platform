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
- Seventeen templates describe patterns that can be inferred from the saved
  card text or images.
- Two templates have `needs_review` status because the saved material is blank
  or too unclear to support a reliable structure.
- Definitions contain no source email copy, links, names, or images.
- The canon explains the common pattern groups, their sequence, and their use.

## Non-goals

- Adding a draft editor, API route, persistence, or template-selection screen.
- Changing stage templates, required asset kinds, or the artifact archive.
- Copying source email text into implementation definitions or new canon prose.
- Guessing the structure of the two unclear examples.
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
5. Given the domain model is added, when existing archive and governance tests
   run, then artifact storage and stage requirements behave as before.
6. Given the canon note is added, when reviewed, then it explains the observed
   patterns in plain words without copying source prose or editing
   `framework-canon/`.

## Constraints

- The pilot covers only the `EMAIL EXAMPLES` list.
- Use the existing archive domain area for the in-memory definitions, but keep
  them separate from archived client artifacts.
- No database, route, or migration changes are needed for this pilot.
- Preserve all unrelated working-tree changes in both repositories.

## Pilot catalog IDs

The catalog uses these stable IDs. The review-needed entries are labeled.

- `appointment_confirmation_prep`
- `authority_interview`
- `interview_collection`
- `bonus_with_purchase` (`needs_review`)
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
- ASSUMPTION: The source cards can be represented by 19 distinct definitions;
  the two unclear cards remain visible in the catalog as review-needed entries.
- Open question: None for this pilot. API and UI use can be specified later.

## Ordered plan

1. Add the email template definition types and 19-entry catalog in
   `backend/redops/contexts/archive/domain/email_templates.py`. Verify unique
   IDs, version, review state, and ordered blocks with a focused unit test in
   `tests/unit/archive/test_email_templates.py`.
2. Add `internal/email-template-structures.md` in `red-canon`. Document the
   19-card analysis as reusable groups and link the source list backup.
3. Run the focused new test and existing archive/governance tests. Review both
   repositories' diffs and ensure unrelated changes remain untouched.

## Rollback

Remove only the new catalog, its focused test, this spec, and the new canon
note. Do not reset either repository or discard other work.
