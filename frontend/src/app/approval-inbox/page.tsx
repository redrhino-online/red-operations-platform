// Route for the approval inbox with exact version diff (SPEC.md section 8;
// Q39). It binds the section 8 screen id `approval-inbox` declared in
// `frontend/dod-screens.txt` to `/approval-inbox`.

import { ApprovalInboxScreen } from "@/features/approval-inbox/ApprovalInboxScreen";

export default function ApprovalInboxPage() {
  return <ApprovalInboxScreen />;
}
