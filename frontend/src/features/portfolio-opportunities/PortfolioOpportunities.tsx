// Portfolio opportunities (SPEC.md sections 3 and 8; DoD condition 6, Q43).
//
// Pure presentational view over the tenant-scoped portfolio opportunity
// register (`GET /red/opportunities`). SPEC.md section 8 lists a "portfolio
// opportunities" screen and requires every artifact view to show state,
// provenance, dependencies and next action; SPEC.md sections 1 and 5 put
// portfolio expansion in the product contract and make the IP Portfolio
// Development agent escalate every investment and launch. The register holds
// proposals only: an opportunity stays `proposed` until a human investment
// authority acts, and its source is grounded on the exact same-tenant approved
// stage asset version it expands (canon files 11 and 12, the Grow motion;
// SPEC.md section 12.3). This view shows each proposal at its pinned source
// version and can approve no investment; it starts no spend and no launch.

import type { PortfolioOpportunity } from "@/shared/api/client";

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
      <h1 id="portfolio-opportunities-heading">Portfolio opportunities</h1>
      <p style={{ color: "var(--red-muted)" }}>
        Proposed expansions for {tenantId ?? "the active client"}, each grounded
        on the exact approved asset version it derives from. A proposal is not an
        investment.
      </p>

      {loading ? <p role="status">Loading portfolio opportunities...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      {!loading && opportunities.length === 0 ? (
        <p data-testid="portfolio-opportunities-empty">
          No portfolio opportunities recorded.
        </p>
      ) : null}

      <h2>Entry points ({entryPoints.length})</h2>
      <ol data-testid="portfolio-entry-points">
        {entryPoints.map((opportunity) => (
          <li
            key={opportunity.opportunity_id}
            data-testid={`portfolio-opportunity-${opportunity.opportunity_id}`}
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

      <h2>Lifetime value ({lifetimeValue.length})</h2>
      <ol data-testid="portfolio-lifetime-value">
        {lifetimeValue.map((opportunity) => (
          <li
            key={opportunity.opportunity_id}
            data-testid={`portfolio-opportunity-${opportunity.opportunity_id}`}
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
    </section>
  );
}
