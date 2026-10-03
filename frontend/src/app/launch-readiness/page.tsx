// Route for the launch readiness screen (SPEC.md section 8; Q41). It binds the
// section 8 screen id `launch-readiness` declared in `frontend/dod-screens.txt`
// to `/launch-readiness`.

import { LaunchReadinessScreen } from "@/features/launch-readiness/LaunchReadinessScreen";

export default function LaunchReadinessPage() {
  return <LaunchReadinessScreen />;
}
