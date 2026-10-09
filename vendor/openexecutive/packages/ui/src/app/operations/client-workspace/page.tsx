// Native cockpit route for the client workspace overview (K3; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). It binds the section
// 8 screen `client-workspace` to `/operations/client-workspace`.

import { ClientWorkspaceScreen } from "@/components/operations/ClientWorkspaceScreen";

export default function ClientWorkspacePage() {
  return <ClientWorkspaceScreen />;
}
