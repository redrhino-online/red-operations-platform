// Native cockpit route for authority settings (K6; SPEC.md section 14 conditions
// 2 and 3, section 8). Additive file (ADR 0014). It binds the section 8 screen
// `authority-settings` to `/operations/authority-settings`.

import { AuthoritySettingsScreen } from "@/components/operations/AuthoritySettingsScreen";

export default function AuthoritySettingsPage() {
  return <AuthoritySettingsScreen />;
}
