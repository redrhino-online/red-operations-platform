// Native cockpit route for the performance review (K6; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). It binds the section
// 8 screen `performance-review` to `/operations/performance-review`.

import { PerformanceReviewScreen } from "@/components/operations/PerformanceReviewScreen";

export default function PerformanceReviewPage() {
  return <PerformanceReviewScreen />;
}
