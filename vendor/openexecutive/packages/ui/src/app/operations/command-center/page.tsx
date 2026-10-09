// Native cockpit route for the portfolio command center (K3; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). It binds the section
// 8 screen `portfolio-command-center` to `/operations/command-center`.

import { CommandCenterScreen } from "@/components/operations/CommandCenterScreen";

export default function CommandCenterPage() {
  return <CommandCenterScreen />;
}
