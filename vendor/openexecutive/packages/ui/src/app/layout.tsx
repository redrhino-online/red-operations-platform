import type { Metadata, Viewport } from "next";
import AuthProvider from "@/components/AuthProvider";
import { ExecutiveStatusProvider } from "@/components/executive/ExecutiveStatusContext";
import { SessionsProvider } from "@/components/sessions/SessionsContext";
import AppShell from "@/components/shell/AppShell";
import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { WorkspaceProvider } from "@/components/workspace/WorkspaceContext";
import "./globals.css";

// RED overlay (ADR 0011): rebrand the shell. The root page carries the
// `RED Operations` identity marker the deployed-health gate requires.
export const metadata: Metadata = {
  title: "RED Operations Platform",
  description: "RED Operations Director for the stage 0 to 10 client pipeline.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full antialiased bg-surface text-fg">
        <AuthProvider>
          <SessionsProvider>
            <ExecutiveStatusProvider>
              <WorkspaceProvider>
                <RedClientProvider>
                  <AppShell>{children}</AppShell>
                </RedClientProvider>
              </WorkspaceProvider>
            </ExecutiveStatusProvider>
          </SessionsProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
