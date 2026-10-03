// Route for the workflow run detail (SPEC.md section 8; Q40). It binds the
// section 8 screen id `workflow-run-detail` declared in `frontend/
// dod-screens.txt` to `/workflow-run-detail`.

import { WorkflowRunDetailScreen } from "@/features/workflow-run/WorkflowRunDetailScreen";

export default function WorkflowRunDetailPage() {
  return <WorkflowRunDetailScreen />;
}
