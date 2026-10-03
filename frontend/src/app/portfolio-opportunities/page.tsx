// Route for the portfolio opportunities screen (SPEC.md section 8; Q43). It
// binds the section 8 screen id `portfolio-opportunities` declared in
// `frontend/dod-screens.txt` to `/portfolio-opportunities`.

import { PortfolioOpportunitiesScreen } from "@/features/portfolio-opportunities/PortfolioOpportunitiesScreen";

export default function PortfolioOpportunitiesPage() {
  return <PortfolioOpportunitiesScreen />;
}
