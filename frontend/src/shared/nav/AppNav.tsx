"use client";

// Persistent RED navigation (Q51; SPEC.md section 8). It renders the section 8
// screens grouped by area and marks the active route. It is a thin client: it
// links only, and grants no authority.

import Link from "next/link";
import { usePathname } from "next/navigation";

import { RED_NAV_GROUPS } from "./screens";

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="RED Operations" data-testid="app-nav">
      {RED_NAV_GROUPS.map((group) => (
        <div key={group.key} className="red-nav-group">
          <p>{group.label}</p>
          <ul>
            {group.screens.map((screen) => {
              const active = pathname === screen.route;
              return (
                <li key={screen.id}>
                  <Link
                    href={screen.route}
                    title={screen.description}
                    aria-current={active ? "page" : undefined}
                  >
                    {screen.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
