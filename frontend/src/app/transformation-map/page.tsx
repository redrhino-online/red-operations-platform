// Route for the transformation map screen (SPEC.md section 8; Q36). It binds the
// section 8 screen id `transformation-map` declared in
// `frontend/dod-screens.txt` to `/transformation-map`.

import { TransformationMapScreen } from "@/features/transformation-map/TransformationMapScreen";

export default function TransformationMapPage() {
  return <TransformationMapScreen />;
}
