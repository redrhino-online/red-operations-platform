// Route for the performance review screen (SPEC.md section 8; Q42). It binds the
// section 8 screen id `performance-review` declared in `frontend/dod-screens.txt`
// to `/performance-review`.

import { PerformanceReviewScreen } from "@/features/performance-review/PerformanceReviewScreen";

export default function PerformanceReviewPage() {
  return <PerformanceReviewScreen />;
}
