// Native cockpit route for the workflow run detail (K4; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). It binds the section
// 8 screen `workflow-run-detail` to `/operations/workflow-run-detail`.

import { WorkflowRunDetailScreen } from "@/components/operations/WorkflowRunDetailScreen";

export default function WorkflowRunDetailPage() {
  return <WorkflowRunDetailScreen />;
}
