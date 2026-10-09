// Native cockpit route for the transformation map (K5; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). It binds the section
// 8 screen `transformation-map` to `/operations/transformation-map`.

import { TransformationMapScreen } from "@/components/operations/TransformationMapScreen";

export default function TransformationMapPage() {
  return <TransformationMapScreen />;
}
