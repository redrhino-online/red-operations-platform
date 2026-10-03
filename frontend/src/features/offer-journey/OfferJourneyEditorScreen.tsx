// Offer and journey editor container (Q37; SPEC.md section 8). It owns the two
// tenant-scoped reads from `GET /red/offers` and `GET /red/journeys` and hands
// the approved offers and authorized releases to the presentational
// `OfferJourneyEditor`. It can approve no offer and authorize no traffic; a read
// authorizes no action.

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  RedOperationsApi,
  type JourneyRelease,
  type OfferVersion,
} from "@/shared/api/client";
import { OfferJourneyEditor } from "./OfferJourneyEditor";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

export function OfferJourneyEditorScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [offers, setOffers] = useState<OfferVersion[]>([]);
  const [journeys, setJourneys] = useState<JourneyRelease[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const [offerPage, journeyPage] = await Promise.all([
        api.listOffers(tenantId),
        api.listJourneys(tenantId),
      ]);
      setOffers(offerPage.offers);
      setJourneys(journeyPage.releases);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load offers and journeys",
      );
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void load();
        }}
      >
        <label>
          Tenant
          <input
            value={tenantId}
            onChange={(event) => setTenantId(event.target.value)}
          />
        </label>
        <button type="submit">Refresh</button>
      </form>
      <OfferJourneyEditor
        offers={offers}
        journeys={journeys}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
