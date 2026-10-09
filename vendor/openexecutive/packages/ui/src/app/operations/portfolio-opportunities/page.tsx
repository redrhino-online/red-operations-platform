// Native cockpit route for the portfolio opportunities register (K6; SPEC.md
// section 14 conditions 2 and 3, section 8). Additive file (ADR 0014). It binds
// the section 8 screen `portfolio-opportunities` to
// `/operations/portfolio-opportunities`.

import { PortfolioOpportunitiesScreen } from "@/components/operations/PortfolioOpportunitiesScreen";

export default function PortfolioOpportunitiesPage() {
  return <PortfolioOpportunitiesScreen />;
}
