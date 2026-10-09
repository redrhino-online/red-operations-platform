"use client";

// Offer and journey editor container, native cockpit page (K5; SPEC.md section
// 14 conditions 2 and 3). Additive file (ADR 0014). It reads the shared
// workspace selection from `useRedClient()` (K2) and owns the two tenant-scoped
// reads from `GET /red/offers` and `GET /red/journeys`; there is no per-screen
// free-text tenant input. It can approve no offer and authorize no traffic; a
// read authorizes no action.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  listJourneys,
  listOffers,
  type JourneyRelease,
  type OfferVersion,
} from "@/lib/redOperationsApi";
import { OfferJourneyEditor } from "./OfferJourneyEditor";

export function OfferJourneyEditorScreen() {
  const { tenantId } = useRedClient();
  const [offers, setOffers] = useState<OfferVersion[]>([]);
  const [journeys, setJourneys] = useState<JourneyRelease[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [offerPage, journeyPage] = await Promise.all([
        listOffers(tenantId),
        listJourneys(tenantId),
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
    <main className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-4">
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
          >
            Refresh
          </button>
        </div>
        <OfferJourneyEditor
          offers={offers}
          journeys={journeys}
          loading={loading}
          error={error}
          tenantId={tenantId}
        />
      </div>
    </main>
  );
}
