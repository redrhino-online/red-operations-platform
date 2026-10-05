// RED Operations Director landing dashboard (Q51; SPEC.md section 8, section 13
// condition 6). It links every section 8 screen, grouped by area, from the same
// single source of truth as the sidebar (`shared/nav/screens.ts`). It is a thin
// client: it reads no state and grants no authority.

import Link from "next/link";

import { RED_NAV_GROUPS } from "@/shared/nav/screens";

export default function Home() {
  return (
    <section>
      <h1>RED Operations Platform</h1>
      <p className="red-lede">
        The RED Operations Director runs the stage 0 to 10 client pipeline. Every
        screen reads state from the RED backend under <code>/red</code> and
        proposes actions; none can grant approval or bypass a gate.
      </p>
      {RED_NAV_GROUPS.map((group) => (
        <section key={group.key} aria-labelledby={`group-${group.key}`}>
          <h2 id={`group-${group.key}`}>{group.label}</h2>
          <ul className="red-card-grid">
            {group.screens.map((screen) => (
              <li key={screen.id} className="red-card">
                <Link href={screen.route}>{screen.label}</Link>
                <p>{screen.description}</p>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </section>
  );
}
