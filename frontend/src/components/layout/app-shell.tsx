"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { AuthGuard } from "@/components/layout/auth-guard";
import { SmtpBanner } from "@/components/layout/smtp-banner";

const AUTH_ROUTES = ["/login", "/setup", "/forgot-password", "/reset-password"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthRoute = AUTH_ROUTES.some((r) => pathname === r || pathname.startsWith(r + "?"));

  if (isAuthRoute) {
    // Auth pages manage their own full-screen layout
    return <>{children}</>;
  }

  return (
    <AuthGuard>
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <SmtpBanner />
          <main className="flex-1 overflow-y-auto">
            <div className="container mx-auto p-6 max-w-7xl">{children}</div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
