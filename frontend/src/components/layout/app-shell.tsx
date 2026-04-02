"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { AuthGuard } from "@/components/layout/auth-guard";
import { SmtpBanner } from "@/components/layout/smtp-banner";

const AUTH_ROUTES = ["/login", "/setup", "/forgot-password", "/reset-password"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isAuthRoute = AUTH_ROUTES.some((r) => pathname === r || pathname.startsWith(r + "?"));

  if (isAuthRoute) {
    // Auth pages manage their own full-screen layout
    return <>{children}</>;
  }

  return (
    <AuthGuard>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Mobile sidebar drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-40 md:hidden transition-transform duration-300 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop sidebar */}
        <Sidebar />

        <div className="flex flex-1 flex-col overflow-hidden min-w-0">
          {/* Mobile top bar */}
          <header className="md:hidden flex items-center gap-3 h-14 px-4 border-b border-slate-800 bg-slate-950 flex-shrink-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded-md p-2 text-slate-400 hover:bg-white/10 hover:text-slate-100 transition-colors"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <Image
              src="/logo.png"
              alt="PricePulse"
              width={28}
              height={28}
              className="object-contain"
            />
            <span className="text-base font-bold tracking-tight bg-gradient-to-r from-[#29ABE2] to-[#8DC63F] bg-clip-text text-transparent">
              PricePulse
            </span>
          </header>

          <SmtpBanner />
          <main className="flex-1 overflow-y-auto">
            <div className="container mx-auto p-4 md:p-6 max-w-7xl">{children}</div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
