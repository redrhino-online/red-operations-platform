// Route for the build board with dependency view (SPEC.md section 8; Q38). It
// binds the section 8 screen id `build-board` declared in
// `frontend/dod-screens.txt` to `/build-board`.

import { BuildBoardScreen } from "@/features/build-board/BuildBoardScreen";

export default function BuildBoardPage() {
  return <BuildBoardScreen />;
}
