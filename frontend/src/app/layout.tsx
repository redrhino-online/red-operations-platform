import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppNav } from "@/shared/nav/AppNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "RED Operations Platform",
  description: "RED Operations Director for the stage 0 to 10 client pipeline.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="red-header">
          <strong>RED Operations Director</strong>
        </header>
        <div className="red-shell">
          <aside className="red-sidebar">
            <AppNav />
          </aside>
          <main className="red-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
