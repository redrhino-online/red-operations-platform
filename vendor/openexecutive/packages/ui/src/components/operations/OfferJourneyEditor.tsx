// Offer and journey editor, native cockpit page (K5; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). Pure presentational
// view over the tenant-scoped approved offers and journey releases the backend
// returns from `GET /red/offers` and `GET /red/journeys`. It renders each stage 5
// production ready offer (audience, promise, eligibility, price hypothesis,
// owner, state and the exact method versions it pins) and each stage 8/9
// authorized journey release (routing, configuration digest, rollback ref and
// the exact asset versions it releases). The offer shape follows canon files 11
// and 12 (Perfect Product, Product Matrix, pricing by outcome); the routing
// shape follows canon files 13, 14, 21 and 22 (CAC funnel, funnel template, page
// set, swimlanes). SPEC.md section 3 makes production require approved
// dependencies and section 4 pins exact versions at a passing gate, so the
// editor shows the approved structure and holds no RED business logic: it can
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
} from "@/lib/redOperationsApi";

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
      <h1 id="offer-journey-heading" className="text-xl font-semibold text-fg">
        Offer and journey editor
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        The stage 5 approved offers and the stage 8/9 authorized journey routing
        for {tenantId ?? "the active client"}: every offer pins its approved
        method versions and every release pins the exact asset versions it sends
        to traffic.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading offers and journeys…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      <section aria-labelledby="offers-heading" className="mt-6">
        <h2 id="offers-heading" className="text-sm font-medium text-fg">
          Approved offers
        </h2>
        <p data-testid="offer-count" className="mt-1 text-sm text-fg-muted">
          {offers.length} approved offer{offers.length === 1 ? "" : "s"}
        </p>
        {!loading && offers.length === 0 ? (
          <p className="mt-1 text-sm text-fg-muted">No approved offers.</p>
        ) : null}

        <div className="mt-3 space-y-4">
          {offers.map((offer) => {
            const refs = pinnedMethodRefs(offer);
            return (
              <article
                key={offer.offer_id}
                aria-label={`Offer ${offer.offer_id}`}
                className="rounded-xl border border-line bg-surface-elevated p-4"
              >
                <h3 className="text-sm font-medium text-fg">
                  {offer.offer_id} <code>{offer.state}</code>
                </h3>
                <p className="mt-1 text-sm text-fg-muted">
                  {offer.is_production_ready
                    ? "production ready"
                    : `not production ready${
                        offer.review_reason ? `: ${offer.review_reason}` : ""
                      }`}
                </p>
                <dl className="mt-2 text-sm text-fg">
                  <dt className="text-fg-muted">Audience</dt>
                  <dd>{offer.audience}</dd>
                  <dt className="text-fg-muted">Promise</dt>
                  <dd>{offer.promise}</dd>
                  <dt className="text-fg-muted">Eligibility</dt>
                  <dd>{offer.eligibility}</dd>
                  <dt className="text-fg-muted">Price hypothesis</dt>
                  <dd>{offer.price_hypothesis}</dd>
                  <dt className="text-fg-muted">Owner</dt>
                  <dd>{offer.owner}</dd>
                </dl>
                <p
                  data-testid={`offer-method-count-${offer.offer_id}`}
                  className="mt-2 text-sm text-fg-muted"
                >
                  {refs.length} pinned method{refs.length === 1 ? "" : "s"}
                </p>
                {refs.length === 0 ? (
                  <p
                    role="alert"
                    className="mt-1 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400"
                  >
                    No approved method dependency is pinned; production requires
                    an approved method.
                  </p>
                ) : (
                  <ul
                    data-testid={`offer-methods-${offer.offer_id}`}
                    className="mt-1 list-disc pl-5 text-sm text-fg"
                  >
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
        </div>
      </section>

      <section aria-labelledby="journeys-heading" className="mt-6">
        <h2 id="journeys-heading" className="text-sm font-medium text-fg">
          Journey routing
        </h2>
        <p data-testid="journey-count" className="mt-1 text-sm text-fg-muted">
          {journeys.length} journey release{journeys.length === 1 ? "" : "s"}
        </p>
        {!loading && journeys.length === 0 ? (
          <p className="mt-1 text-sm text-fg-muted">
            No authorized journey releases.
          </p>
        ) : null}

        <div className="mt-3 space-y-4">
          {journeys.map((journey) => (
            <article
              key={journey.release_id}
              aria-label={`Journey ${journey.release_id}`}
              className="rounded-xl border border-line bg-surface-elevated p-4"
            >
              <h3 className="text-sm font-medium text-fg">
                {journey.release_id} <code>{journey.routing}</code>
              </h3>
              <p className="mt-1 text-sm text-fg-muted">
                {journey.is_authorized
                  ? `authorized release grounded on ${journey.qa_id}`
                  : "not authorized"}
                {journey.is_signed_ready ? " (signed ready)" : ""}
              </p>
              <dl className="mt-2 text-sm text-fg">
                <dt className="text-fg-muted">Configuration digest</dt>
                <dd>
                  <code>{journey.configuration_digest}</code>
                </dd>
                <dt className="text-fg-muted">Rollback ref</dt>
                <dd>
                  <code>{journey.rollback_ref}</code>
                </dd>
                <dt className="text-fg-muted">Released kinds</dt>
                <dd data-testid={`journey-kinds-${journey.release_id}`}>
                  {listLabel(releasedAssetKinds(journey))}
                </dd>
              </dl>
              <div className="mt-2 overflow-x-auto rounded-lg border border-line bg-surface">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-fg-muted">
                    <tr className="border-b border-line">
                      <th scope="col" className="px-3 py-2 font-medium">Asset</th>
                      <th scope="col" className="px-3 py-2 font-medium">Kind</th>
                      <th scope="col" className="px-3 py-2 font-medium">Version</th>
                    </tr>
                  </thead>
                  <tbody>
                    {journey.assets.map((asset) => (
                      <tr
                        key={asset.asset_id}
                        className="border-b border-line last:border-0"
                      >
                        <td className="px-3 py-2 text-fg">{asset.asset_id}</td>
                        <td className="px-3 py-2 text-fg">{asset.kind}</td>
                        <td className="px-3 py-2 text-fg">{asset.version}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
