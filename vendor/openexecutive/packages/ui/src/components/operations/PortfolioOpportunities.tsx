// Portfolio opportunities, native cockpit page (K6; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). Pure presentational
// view over the tenant-scoped portfolio opportunity register
// (`GET /red/opportunities`). SPEC.md section 8 lists a "portfolio
// opportunities" screen and requires every artifact view to show state,
// provenance, dependencies and next action; SPEC.md sections 1 and 5 put
// portfolio expansion in the product contract and make the IP Portfolio
// Development agent escalate every investment and launch. The register holds
// proposals only: an opportunity stays `proposed` until a human investment
// authority acts, and its source is grounded on the exact same-tenant approved
// stage asset version it expands (canon files 11 and 12, the Grow motion;
// SPEC.md section 12.3). This view shows each proposal at its pinned source
// version and can approve no investment; it starts no spend and no launch.

import type { PortfolioOpportunity } from "@/lib/redOperationsApi";

export interface PortfolioOpportunitiesProps {
  opportunities: PortfolioOpportunity[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
}

// The canon's two Grow effects: a smaller offer that becomes a new entry point,
// or one that raises customer lifetime value (canon files 11 and 12). The
// register refuses an untyped expansion, so the two groups are exhaustive.
export const ENTRY_POINT = "entry_point";
export const LIFETIME_VALUE = "lifetime_value";

// Provenance: an opportunity is never shown without the exact version of the
// approved asset it derives from (SPEC.md sections 3 and 4).
export function groundingVersion(opportunity: PortfolioOpportunity): string {
  return `${opportunity.source_asset_id}@v${opportunity.source_version}`;
}

// Group the register by the canon's Grow effect so a reader sees the entry
// points and the lifetime value offers apart; order within a group is the
// register order the API returned.
export function byKind(
  opportunities: PortfolioOpportunity[],
  kind: string,
): PortfolioOpportunity[] {
  return opportunities.filter((opportunity) => opportunity.kind === kind);
}

// The register never represents a proposal as an approved investment, so a row
// that is not `proposed` is surfaced as-is rather than as approved (SPEC.md
// sections 1 and 5).
export function isProposal(opportunity: PortfolioOpportunity): boolean {
  return opportunity.state === "proposed";
}

function OpportunityList({
  opportunities,
  testId,
}: {
  opportunities: PortfolioOpportunity[];
  testId: string;
}) {
  return (
    <ol data-testid={testId} className="mt-2 space-y-3 text-sm text-fg">
      {opportunities.map((opportunity) => (
        <li
          key={opportunity.opportunity_id}
          data-testid={`portfolio-opportunity-${opportunity.opportunity_id}`}
          className="rounded-lg border border-line bg-surface p-3"
        >
          <strong>{opportunity.title}</strong> ({opportunity.state})
          <br />
          Grounded on: {groundingVersion(opportunity)} (source kind:{" "}
          {opportunity.source_kind})
          <br />
          Expected outcome: {opportunity.expected_outcome}
          <br />
          Investment case: {opportunity.investment_case}
          <br />
          Owner: {opportunity.owner} | Next action: {opportunity.next_action} |
          Captured: {opportunity.captured_on}
        </li>
      ))}
    </ol>
  );
}

export function PortfolioOpportunities({
  opportunities,
  loading = false,
  error = null,
  tenantId,
}: PortfolioOpportunitiesProps) {
  const entryPoints = byKind(opportunities, ENTRY_POINT);
  const lifetimeValue = byKind(opportunities, LIFETIME_VALUE);

  return (
    <section aria-labelledby="portfolio-opportunities-heading">
      <h1
        id="portfolio-opportunities-heading"
        className="text-xl font-semibold text-fg"
      >
        Portfolio opportunities
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        Proposed expansions for {tenantId ?? "the active client"}, each grounded
        on the exact approved asset version it derives from. A proposal is not an
        investment.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading portfolio opportunities…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      {!loading && opportunities.length === 0 ? (
        <p
          data-testid="portfolio-opportunities-empty"
          className="mt-4 text-sm text-fg-muted"
        >
          No portfolio opportunities recorded.
        </p>
      ) : null}

      <h2 className="mt-6 text-sm font-medium text-fg">
        Entry points ({entryPoints.length})
      </h2>
      <OpportunityList opportunities={entryPoints} testId="portfolio-entry-points" />

      <h2 className="mt-6 text-sm font-medium text-fg">
        Lifetime value ({lifetimeValue.length})
      </h2>
      <OpportunityList
        opportunities={lifetimeValue}
        testId="portfolio-lifetime-value"
      />
    </section>
  );
}
