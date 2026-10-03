// Route for the offer and journey editor screen (SPEC.md section 8; Q37). It
// binds the section 8 screen id `offer-and-journey-editor` declared in
// `frontend/dod-screens.txt` to `/offer-and-journey`.

import { OfferJourneyEditorScreen } from "@/features/offer-journey/OfferJourneyEditorScreen";

export default function OfferAndJourneyPage() {
  return <OfferJourneyEditorScreen />;
}
