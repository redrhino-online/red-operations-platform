// Route for the portfolio command center screen (SPEC.md section 8; Q33). It
// binds the section 8 screen id `portfolio-command-center` declared in
// `frontend/dod-screens.txt` to `/command-center`.

import { CommandCenterScreen } from "@/features/command-center/CommandCenterScreen";

export default function CommandCenterPage() {
  return <CommandCenterScreen />;
}
