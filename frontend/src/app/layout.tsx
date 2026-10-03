import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "RED Operations Platform",
  description: "RED Operations Director for the stage 0 to 10 client pipeline.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header
          style={{
            background: "var(--red-primary)",
            color: "white",
            padding: "0.75rem 1.5rem",
          }}
        >
          <strong>RED Operations Director</strong>
        </header>
        <main style={{ padding: "1.5rem", maxWidth: "64rem", margin: "0 auto" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
