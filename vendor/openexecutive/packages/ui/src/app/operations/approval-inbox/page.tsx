// Native cockpit route for the approval inbox (K3; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). It binds the section
// 8 screen `approval-inbox` to `/operations/approval-inbox`.

import { ApprovalInboxScreen } from "@/components/operations/ApprovalInboxScreen";

export default function ApprovalInboxPage() {
  return <ApprovalInboxScreen />;
}
