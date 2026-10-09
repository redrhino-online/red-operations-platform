// Source and claim explorer, native cockpit page (K5; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). Pure presentational
// view over the tenant-scoped source records and claims the backend returns from
// `GET /red/clients/{id}/sources` and `GET /red/claims`. It holds no RED
// business logic: it renders each source's provenance (locator, checksum,
// capture time, access rule) and each claim's statement, provenance class,
// confidence note and citations, and shows which source grounds which claim. It
// can set no provenance class, add no citation and approve no claim; the backend
// owns every claim rule (SPEC.md sections 3 and 11).

import type { Claim, SourceRecord } from "@/lib/redOperationsApi";

export interface SourceClaimExplorerProps {
  sources: SourceRecord[];
  claims: Claim[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
}

// The claims that cite a given immutable source, so the explorer shows a
// source's grounded claims rather than a flat unrelated list. This is a
// presentation projection: it reads the citations the backend already verified.
export function claimsForSource(claims: Claim[], sourceId: string): Claim[] {
  return claims.filter((claim) =>
    claim.citations.some((citation) => citation.source_id === sourceId),
  );
}

// A claim carries a direct source, or it does not. A directly sourced claim is
// the only shape that can be Known (SPEC.md section 3); the explorer shows this
// flag so a Derived or Proposed claim is never read as a Known fact.
export function groundedClaims(claims: Claim[]): Claim[] {
  return claims.filter((claim) => claim.is_directly_sourced);
}

function citationLabel(citation: {
  source_id: string;
  checksum: string;
  location: string;
}): string {
  return `${citation.source_id}@${citation.checksum} (${citation.location})`;
}

export function SourceClaimExplorer({
  sources,
  claims,
  loading = false,
  error = null,
  tenantId,
}: SourceClaimExplorerProps) {
  return (
    <section aria-labelledby="source-explorer-heading">
      <h1 id="source-explorer-heading" className="text-xl font-semibold text-fg">
        Source and claim explorer
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        Immutable sources and the claims they ground for{" "}
        {tenantId ?? "the active client"}. A claim cites an exact source checksum
        and location; the platform never presents an unsourced claim as Known.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading sources and claims…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      <p data-testid="source-count" className="mt-4 text-sm text-fg-muted">
        {sources.length} source{sources.length === 1 ? "" : "s"}
      </p>
      <p data-testid="claim-count" className="text-sm text-fg-muted">
        {claims.length} claim{claims.length === 1 ? "" : "s"},{" "}
        {groundedClaims(claims).length} directly sourced
      </p>

      {!loading && sources.length === 0 ? (
        <p className="mt-2 text-sm text-fg-muted">No sources.</p>
      ) : null}

      {sources.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface-elevated">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-fg-muted">
              <tr className="border-b border-line">
                <th scope="col" className="px-3 py-2 font-medium">Locator</th>
                <th scope="col" className="px-3 py-2 font-medium">Checksum</th>
                <th scope="col" className="px-3 py-2 font-medium">Captured</th>
                <th scope="col" className="px-3 py-2 font-medium">Access rule</th>
                <th scope="col" className="px-3 py-2 font-medium">Grounded claims</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => {
                const grounded = claimsForSource(claims, source.source_id);
                return (
                  <tr
                    key={source.source_id}
                    className="border-b border-line last:border-0"
                  >
                    <td className="px-3 py-2 text-fg">{source.locator}</td>
                    <td className="px-3 py-2 text-fg">
                      <code>{source.checksum}</code>
                    </td>
                    <td className="px-3 py-2 text-fg">{source.captured_on}</td>
                    <td className="px-3 py-2 text-fg">{source.access_rule}</td>
                    <td className="px-3 py-2 text-fg">
                      {grounded.map((claim) => claim.claim_id).join(", ") || "none"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {!loading && claims.length === 0 ? (
        <p className="mt-4 text-sm text-fg-muted">No claims.</p>
      ) : null}

      {claims.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface-elevated">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-fg-muted">
              <tr className="border-b border-line">
                <th scope="col" className="px-3 py-2 font-medium">Provenance</th>
                <th scope="col" className="px-3 py-2 font-medium">Statement</th>
                <th scope="col" className="px-3 py-2 font-medium">Confidence note</th>
                <th scope="col" className="px-3 py-2 font-medium">Citations</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr
                  key={claim.claim_id}
                  className="border-b border-line last:border-0 align-top"
                >
                  <td className="px-3 py-2 text-fg">
                    <strong>{claim.provenance}</strong>
                    <br />
                    <span className="text-fg-muted">
                      {claim.is_directly_sourced
                        ? "direct source"
                        : "no direct source"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-fg">{claim.statement}</td>
                  <td className="px-3 py-2 text-fg">{claim.confidence_note}</td>
                  <td className="px-3 py-2 text-fg">
                    {claim.citations.map(citationLabel).join(", ") || "none"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
