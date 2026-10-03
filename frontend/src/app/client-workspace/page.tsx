// Route for the client workspace overview screen (SPEC.md section 8; Q34). It
// binds the section 8 screen id `client-workspace-overview` declared in
// `frontend/dod-screens.txt` to `/client-workspace`.

import { ClientWorkspaceOverviewScreen } from "@/features/client-workspace/ClientWorkspaceOverviewScreen";

export default function ClientWorkspacePage() {
  return <ClientWorkspaceOverviewScreen />;
}
