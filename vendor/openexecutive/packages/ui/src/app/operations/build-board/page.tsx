// Native cockpit route for the build board with dependency view (K4; SPEC.md
// section 14 conditions 2 and 3, section 8). Additive file (ADR 0014). It binds
// the section 8 screen `build-board` to `/operations/build-board`.

import { BuildBoardScreen } from "@/components/operations/BuildBoardScreen";

export default function BuildBoardPage() {
  return <BuildBoardScreen />;
}
