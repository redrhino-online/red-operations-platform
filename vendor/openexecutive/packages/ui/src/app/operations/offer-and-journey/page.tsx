// Native cockpit route for the offer and journey editor (K5; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). It binds the section
// 8 screen `offer-and-journey` to `/operations/offer-and-journey`.

import { OfferJourneyEditorScreen } from "@/components/operations/OfferJourneyEditorScreen";

export default function OfferAndJourneyPage() {
  return <OfferJourneyEditorScreen />;
}
