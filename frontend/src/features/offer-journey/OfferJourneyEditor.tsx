// Offer and journey editor (SPEC.md section 8; DoD condition 6, Q37).
//
// Pure presentational view over the tenant-scoped approved offers and journey
// releases the backend returns from `GET /red/offers` and `GET /red/journeys`.
// It renders each stage 5 production ready offer (audience, promise, eligibility,
// price hypothesis, owner, state and the exact method versions it pins) and each
// stage 8/9 authorized journey release (routing, configuration digest, rollback
// ref and the exact asset versions it releases). The offer shape follows canon
// files 11 and 12 (Perfect Product, Product Matrix, pricing by outcome); the
// routing shape follows canon files 13, 14, 21 and 22 (CAC funnel, funnel
// template, page set, swimlanes). SPEC.md section 3 makes production require
// approved dependencies and section 4 pins exact versions at a passing gate, so
// the editor shows the approved structure and holds no RED business logic: it can
// approve no offer and authorize no traffic.
//
// SPEC.md section 12.4: canon 11-12 (stage 5 offer), canon 13-14, 21-22 (stage 8
// journey routing). Deviations: RED narrows the offer to the section 3 required
// fields and the release to the section 3 JourneyRelease fields; a client
// process is a separate stage 8/9 artifact, not shown here.

import type {
  JourneyRelease,
  MethodReference,
  OfferVersion,
} from "@/shared/api/client";

export interface OfferJourneyEditorProps {
  offers: OfferVersion[];
  journeys: JourneyRelease[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
}

// The exact method versions an offer pins, sorted deterministically by intended
// use then method id. The backend returns the pinned set in its own order; this
// only stabilizes display and loses no reference.
export function pinnedMethodRefs(offer: OfferVersion): MethodReference[] {
  return [...offer.method_refs].sort((left, right) => {
    const byUse = left.intended_use.localeCompare(right.intended_use);
    return byUse !== 0 ? byUse : left.method_id.localeCompare(right.method_id);
  });
}

// The asset kinds a journey release pins, sorted for stable display. The
// aggregate already refuses a duplicate kind, so this is a view ordering only.
export function releasedAssetKinds(journey: JourneyRelease): string[] {
  return [...journey.released_kinds].sort();
}

function listLabel(entries: string[]): string {
  return entries.join(", ") || "none";
}

export function OfferJourneyEditor({
  offers,
  journeys,
  loading = false,
  error = null,
  tenantId,
}: OfferJourneyEditorProps) {
  return (
    <section aria-labelledby="offer-journey-heading">
      <h1 id="offer-journey-heading">Offer and journey editor</h1>
      <p style={{ color: "var(--red-muted)" }}>
        The stage 5 approved offers and the stage 8/9 authorized journey routing
        for {tenantId ?? "the active client"}: every offer pins its approved
        method versions and every release pins the exact asset versions it sends
        to traffic.
      </p>

      {loading ? <p role="status">Loading offers and journeys...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <section aria-labelledby="offers-heading">
        <h2 id="offers-heading">Approved offers</h2>
        <p data-testid="offer-count">
          {offers.length} approved offer{offers.length === 1 ? "" : "s"}
        </p>
        {!loading && offers.length === 0 ? <p>No approved offers.</p> : null}

        {offers.map((offer) => {
          const refs = pinnedMethodRefs(offer);
          return (
            <article key={offer.offer_id} aria-label={`Offer ${offer.offer_id}`}>
              <h3>
                {offer.offer_id} <code>{offer.state}</code>
              </h3>
              <p>
                {offer.is_production_ready
                  ? "production ready"
                  : `not production ready${
                      offer.review_reason ? `: ${offer.review_reason}` : ""
                    }`}
              </p>
              <dl>
                <dt>Audience</dt>
                <dd>{offer.audience}</dd>
                <dt>Promise</dt>
                <dd>{offer.promise}</dd>
                <dt>Eligibility</dt>
                <dd>{offer.eligibility}</dd>
                <dt>Price hypothesis</dt>
                <dd>{offer.price_hypothesis}</dd>
                <dt>Owner</dt>
                <dd>{offer.owner}</dd>
              </dl>
              <p data-testid={`offer-method-count-${offer.offer_id}`}>
                {refs.length} pinned method{refs.length === 1 ? "" : "s"}
              </p>
              {refs.length === 0 ? (
                <p role="alert">
                  No approved method dependency is pinned; production requires
                  an approved method.
                </p>
              ) : (
                <ul data-testid={`offer-methods-${offer.offer_id}`}>
                  {refs.map((reference) => (
                    <li key={`${reference.method_id}-${reference.version}`}>
                      {reference.method_id} <code>{reference.version}</code> for{" "}
                      {reference.intended_use}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          );
        })}
      </section>

      <section aria-labelledby="journeys-heading">
        <h2 id="journeys-heading">Journey routing</h2>
        <p data-testid="journey-count">
          {journeys.length} journey release{journeys.length === 1 ? "" : "s"}
        </p>
        {!loading && journeys.length === 0 ? (
          <p>No authorized journey releases.</p>
        ) : null}

        {journeys.map((journey) => (
          <article
            key={journey.release_id}
            aria-label={`Journey ${journey.release_id}`}
          >
            <h3>
              {journey.release_id} <code>{journey.routing}</code>
            </h3>
            <p>
              {journey.is_authorized
                ? `authorized release grounded on ${journey.qa_id}`
                : "not authorized"}
              {journey.is_signed_ready ? " (signed ready)" : ""}
            </p>
            <dl>
              <dt>Configuration digest</dt>
              <dd>
                <code>{journey.configuration_digest}</code>
              </dd>
              <dt>Rollback ref</dt>
              <dd>
                <code>{journey.rollback_ref}</code>
              </dd>
              <dt>Released kinds</dt>
              <dd data-testid={`journey-kinds-${journey.release_id}`}>
                {listLabel(releasedAssetKinds(journey))}
              </dd>
            </dl>
            <table>
              <thead>
                <tr>
                  <th scope="col">Asset</th>
                  <th scope="col">Kind</th>
                  <th scope="col">Version</th>
                </tr>
              </thead>
              <tbody>
                {journey.assets.map((asset) => (
                  <tr key={asset.asset_id}>
                    <td>{asset.asset_id}</td>
                    <td>{asset.kind}</td>
                    <td>{asset.version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        ))}
      </section>
    </section>
  );
}
