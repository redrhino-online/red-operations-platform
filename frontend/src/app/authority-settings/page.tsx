// Route for the authority settings screen (SPEC.md section 8; Q44). It binds the
// section 8 screen id `authority-settings` declared in `frontend/dod-screens.txt`
// to `/authority-settings`.

import { AuthoritySettingsScreen } from "@/features/authority-settings/AuthoritySettingsScreen";

export default function AuthoritySettingsPage() {
  return <AuthoritySettingsScreen />;
}
