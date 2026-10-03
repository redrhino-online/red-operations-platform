// Route for the source and claim explorer screen (SPEC.md section 8; Q35). It
// binds the section 8 screen id `source-and-claim-explorer` declared in
// `frontend/dod-screens.txt` to `/source-explorer`.

import { SourceClaimExplorerScreen } from "@/features/source-explorer/SourceClaimExplorerScreen";

export default function SourceExplorerPage() {
  return <SourceClaimExplorerScreen />;
}
