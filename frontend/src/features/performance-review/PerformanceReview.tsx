// Performance review (SPEC.md sections 4 and 8; DoD condition 6, Q42).
//
// Pure presentational view over two tenant-scoped reads: the production-manager
// view (`GET /red/clients/{tenant}/engagements/{engagement}/production-view`),
// which carries the stage 10 "Performance Baseline Established" gate state and
// its exact pinned baseline asset versions, and the stage 10 measurement
// registry (`GET /red/measurements`), which carries the post-launch
// observations. SPEC.md section 4, stage 10, treats first qualified traffic and
// the subsequent lead, appointment and sale as distinct observed milestones and
// requires missing observations to be shown as pending, never omitted or filled
// with a guess. This view maps each milestone to the funnel step the canon's
// Metrics Matrix solves down (canon files 22-24, SPEC.md section 12.3:
// audience, leads, strategy sessions, customers) and marks a milestone observed
// only when an observed (not placeholder) record exists, otherwise pending. It
// computes no metric and starts no optimization; the stage 10 gate owns the
// baseline, so the view can release and change nothing.

import type {
  EngagementProductionView,
  MeasurementRecord,
  StageProductionView,
} from "@/shared/api/client";

export interface PerformanceReviewProps {
  view: EngagementProductionView | null;
  measurements: MeasurementRecord[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
}

// The four distinct stage 10 post-launch milestones, in canonical order
// (SPEC.md section 4, stage 10).
export const MILESTONE_KINDS: readonly string[] = [
  "first_qualified_traffic",
  "lead",
  "appointment",
  "sale",
];

// Each milestone is read from the funnel step the Metrics Matrix solves down:
// first qualified traffic is the audience step, a strategy session is the
// appointment step, and a customer is the sale (canon files 23 and 24).
export const MILESTONE_FUNNEL_STEP: Record<string, string> = {
  first_qualified_traffic: "audience",
  lead: "lead",
  appointment: "appointment",
  sale: "customer",
};

export interface MilestoneState {
  kind: string;
  status: "observed" | "pending";
  record: MeasurementRecord | null;
}

// The stage 10 baseline gate row, or null when the view has no stage 10.
export function baselineStage(
  view: EngagementProductionView | null,
): StageProductionView | null {
  if (view === null) {
    return null;
  }
  return view.stages.find((stage) => stage.stage_number === 10) ?? null;
}

// Provenance: an approved baseline asset is only ever shown at an exact pinned
// version.
export function baselinePins(stage: StageProductionView | null): string[] {
  if (stage === null) {
    return [];
  }
  return stage.approved_assets.map(
    (asset) => `${asset.asset_id}@v${asset.version}`,
  );
}

// The newest observed record per milestone. A placeholder (`is_observed` false)
// is not a measured result, so it leaves the milestone pending rather than
// filling a missing observation with a guess (SPEC.md section 4, stage 10).
export function milestoneStates(
  records: MeasurementRecord[],
): MilestoneState[] {
  const observed = records.filter((record) => record.is_observed);
  return MILESTONE_KINDS.map((kind) => {
    const step = MILESTONE_FUNNEL_STEP[kind];
    const matches = observed.filter(
      (record) => record.metric.funnel_step === step,
    );
    const record = matches.reduce<MeasurementRecord | null>(
      (newest, candidate) =>
        newest === null || candidate.recorded_on > newest.recorded_on
          ? candidate
          : newest,
      null,
    );
    return {
      kind,
      status: record === null ? "pending" : "observed",
      record,
    };
  });
}

function display(value: string | null): string {
  return value === null || value === "" ? "none" : value;
}

export function PerformanceReview({
  view,
  measurements,
  loading = false,
  error = null,
  tenantId,
}: PerformanceReviewProps) {
  const stage = baselineStage(view);
  const milestones = milestoneStates(measurements);

  return (
    <section aria-labelledby="performance-review-heading">
      <h1 id="performance-review-heading">Performance review</h1>
      <p style={{ color: "var(--red-muted)" }}>
        The stage 10 performance baseline for {tenantId ?? "the active client"}:
        its gate state, the exact pinned baseline assets and the post-launch
        milestones observed so far.
      </p>

      {loading ? <p role="status">Loading performance review...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <h2>Stage 10 baseline</h2>
      <div data-testid="performance-baseline">
        {stage === null ? (
          <p>No stage 10 baseline.</p>
        ) : (
          <>
            <p data-testid="performance-baseline-state">
              {stage.name} ({stage.checkpoint}):{" "}
              {stage.is_approved ? "approved" : stage.status}
            </p>
            <p data-testid="performance-baseline-assets">
              Pinned baseline assets:{" "}
              {baselinePins(stage).join(", ") || "none"}
            </p>
            <p data-testid="performance-baseline-missing">
              Missing: {stage.missing_asset_kinds.join(", ") || "none"}
            </p>
            <p data-testid="performance-baseline-owner">
              Owner: {display(stage.assigned_owner ?? stage.accountable_role)} |
              Due: {display(stage.due_on)}
            </p>
            <p data-testid="performance-baseline-next">
              Next action: {stage.next_action || "none"}
            </p>
            {stage.blockers.length > 0 ? (
              <p data-testid="performance-baseline-blockers">
                Blockers: {stage.blockers.join(", ")}
              </p>
            ) : null}
          </>
        )}
      </div>

      <h2>Post-launch milestones</h2>
      <ol data-testid="performance-milestones">
        {milestones.map((milestone) => (
          <li
            key={milestone.kind}
            data-testid={`performance-milestone-${milestone.kind}`}
          >
            <strong>{milestone.kind}</strong>: {milestone.status}
            {milestone.record === null ? null : (
              <>
                {" "}
                value {milestone.record.value}{" "}
                {milestone.record.metric.unit} ({milestone.record.window_start}{" "}
                to {milestone.record.window_end}) | source:{" "}
                {milestone.record.source} | basis: {milestone.record.basis}
              </>
            )}
          </li>
        ))}
      </ol>

      {!loading && measurements.length === 0 ? (
        <p data-testid="performance-no-observations">
          No post-launch observations recorded.
        </p>
      ) : null}
    </section>
  );
}
