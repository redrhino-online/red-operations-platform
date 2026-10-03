// Source and claim explorer (SPEC.md section 8; DoD condition 6, Q35).
//
// Pure presentational view over the tenant-scoped source records and claims the
// backend returns from `GET /red/clients/{id}/sources` and `GET /red/claims`. It
// holds no RED business logic: it renders each source's provenance (locator,
// checksum, capture time, access rule) and each claim's statement, provenance
// class, confidence note and citations, and shows which source grounds which
// claim. It can set no provenance class, add no citation and approve no claim;
// the backend owns every claim rule (SPEC.md sections 3 and 11).

import type { Claim, SourceRecord } from "@/shared/api/client";

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
      <h1 id="source-explorer-heading">Source and claim explorer</h1>
      <p style={{ color: "var(--red-muted)" }}>
        Immutable sources and the claims they ground for{" "}
        {tenantId ?? "the active client"}. A claim cites an exact source checksum
        and location; the platform never presents an unsourced claim as Known.
      </p>

      {loading ? <p role="status">Loading sources and claims...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <p data-testid="source-count">
        {sources.length} source{sources.length === 1 ? "" : "s"}
      </p>
      <p data-testid="claim-count">
        {claims.length} claim{claims.length === 1 ? "" : "s"},{" "}
        {groundedClaims(claims).length} directly sourced
      </p>

      {!loading && sources.length === 0 ? <p>No sources.</p> : null}

      {sources.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th scope="col">Locator</th>
              <th scope="col">Checksum</th>
              <th scope="col">Captured</th>
              <th scope="col">Access rule</th>
              <th scope="col">Grounded claims</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => {
              const grounded = claimsForSource(claims, source.source_id);
              return (
                <tr key={source.source_id}>
                  <td>{source.locator}</td>
                  <td>
                    <code>{source.checksum}</code>
                  </td>
                  <td>{source.captured_on}</td>
                  <td>{source.access_rule}</td>
                  <td>{grounded.map((claim) => claim.claim_id).join(", ") || "none"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}

      {!loading && claims.length === 0 ? <p>No claims.</p> : null}

      {claims.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th scope="col">Provenance</th>
              <th scope="col">Statement</th>
              <th scope="col">Confidence note</th>
              <th scope="col">Citations</th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td>
                  <strong>{claim.provenance}</strong>
                  <br />
                  <span style={{ color: "var(--red-muted)" }}>
                    {claim.is_directly_sourced ? "direct source" : "no direct source"}
                  </span>
                </td>
                <td>{claim.statement}</td>
                <td>{claim.confidence_note}</td>
                <td>
                  {claim.citations.map(citationLabel).join(", ") || "none"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
