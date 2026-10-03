// Launch readiness (SPEC.md sections 4 and 8; DoD condition 6, Q41).
//
// Pure presentational view over the tenant-scoped authorized stage 9 launch QAs
// the backend returns from `GET /red/launch-qas`. A launch QA pins the stage 9
// "Launch Approved" evidence: every required check with its outcome, evidence
// and owner, and the designated human's traffic authorization (SPEC.md section
// 4, stage 9). This view surfaces the state, the critical-path failures and the
// excepted checks that block or qualify readiness, and the exact pinned
// authorization. It asserts no gate rule, resolves no authority and authorizes
// no traffic; the stage 9 gate owns readiness, so the view can release nothing.

import type { LaunchQA, LaunchQACheck } from "@/shared/api/client";

export interface LaunchReadinessProps {
  launchQas: LaunchQA[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
}

function display(value: string | null): string {
  return value === null || value === "" ? "none" : value;
}

// A check outcome is exact, so the view groups by the recorded outcome rather
// than inferring readiness from the presence of a check.
export function checksWithOutcome(
  qa: LaunchQA,
  outcome: string,
): LaunchQACheck[] {
  return qa.checks.filter((check) => check.outcome === outcome);
}

// The failed critical-path checks that block "Launch Approved". An off-critical
// check may be excepted with an owner, but a critical failure never authorizes
// traffic (SPEC.md sections 4 and 5).
export function criticalFailures(qa: LaunchQA): LaunchQACheck[] {
  return qa.checks.filter(
    (check) => check.outcome === "failed" && check.is_critical_path,
  );
}

// The explicitly excepted checks. Each names a human risk owner, so an
// exception is a scoped decision rather than a silent omission.
export function exceptions(qa: LaunchQA): LaunchQACheck[] {
  return checksWithOutcome(qa, "excepted");
}

// Whether the QA pins a designated human's authorization to begin traffic. A
// ready state without a pinned authorization is not readiness.
export function isAuthorized(qa: LaunchQA): boolean {
  return qa.is_ready_for_traffic && qa.authorization !== null;
}

export function LaunchReadiness({
  launchQas,
  loading = false,
  error = null,
  tenantId,
}: LaunchReadinessProps) {
  return (
    <section aria-labelledby="launch-readiness-heading">
      <h1 id="launch-readiness-heading">Launch readiness</h1>
      <p style={{ color: "var(--red-muted)" }}>
        The stage 9 launch QA for {tenantId ?? "the active client"}: its required
        checks, exceptions and the designated human&apos;s traffic
        authorization.
      </p>

      {loading ? <p role="status">Loading launch readiness...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <p data-testid="launch-qa-count">
        {launchQas.length} launch QA{launchQas.length === 1 ? "" : "s"}
      </p>

      {!loading && launchQas.length === 0 ? <p>No launch QAs.</p> : null}

      {launchQas.map((qa) => {
        const failures = criticalFailures(qa);
        const excepted = exceptions(qa);
        const passed = checksWithOutcome(qa, "passed");
        return (
          <article key={qa.qa_id} aria-label={`Launch QA ${qa.qa_id}`}>
            <h2 data-testid={`launch-qa-${qa.qa_id}`}>{qa.qa_id}</h2>
            <p data-testid={`launch-state-${qa.qa_id}`}>
              State: {qa.state} |{" "}
              {isAuthorized(qa) ? "Ready for traffic" : "Not authorized"}
            </p>
            <p data-testid={`launch-owner-${qa.qa_id}`}>
              Owner: {qa.owner} | Designated authority:{" "}
              {qa.designated_authority}
            </p>
            <p>
              Checks: {passed.length} passed | {failures.length} critical failed
              | {excepted.length} excepted
            </p>
            {qa.review_reason !== null ? (
              <p data-testid={`launch-review-${qa.qa_id}`}>
                Review required: {qa.review_reason}
              </p>
            ) : null}

            <h3>Critical-path failures</h3>
            <div data-testid={`launch-failures-${qa.qa_id}`}>
              {failures.length === 0 ? (
                <p>No critical-path failures.</p>
              ) : (
                <ul>
                  {failures.map((check) => (
                    <li key={check.kind}>
                      {check.kind}: {check.evidence}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <h3>Exceptions</h3>
            <div data-testid={`launch-exceptions-${qa.qa_id}`}>
              {excepted.length === 0 ? (
                <p>No excepted checks.</p>
              ) : (
                <ul>
                  {excepted.map((check) => (
                    <li key={check.kind}>
                      {check.kind}: {check.outcome} | owner:{" "}
                      {display(check.owner)} | {check.evidence}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <h3>Traffic authorization</h3>
            <div data-testid={`launch-authorization-${qa.qa_id}`}>
              {qa.authorization === null ? (
                <p>No traffic authorization pinned.</p>
              ) : (
                <>
                  <p>Authorized by: {qa.authorization.authorized_by}</p>
                  <p>Intended use: {qa.authorization.intended_use}</p>
                  <p>Authorized on: {qa.authorization.authorized_on}</p>
                </>
              )}
            </div>

            <h3>Checks</h3>
            <ol data-testid={`launch-checks-${qa.qa_id}`}>
              {qa.checks.map((check) => (
                <li key={check.kind} data-testid={`launch-check-${qa.qa_id}-${check.kind}`}>
                  <p>
                    <strong>{check.kind}</strong>: {check.outcome}
                    {check.is_critical_path ? " (critical path)" : ""}
                  </p>
                  <p>Evidence: {check.evidence}</p>
                  <p>Owner: {display(check.owner)}</p>
                </li>
              ))}
            </ol>
          </article>
        );
      })}
    </section>
  );
}
