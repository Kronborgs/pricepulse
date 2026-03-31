"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot,
  Eye,
  LayoutDashboard,
  LogOut,
  Mail,
  Package,
  Database,
  Settings,
  ShieldAlert,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

const mainNavItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/watches", label: "Watches", icon: Eye },
  { href: "/products", label: "Produkter", icon: Package },
  { href: "/settings", label: "Indstillinger", icon: Settings },
];

const adminNavItems = [
  { href: "/admin/ai-log", label: "AI Job Log", icon: Bot },
  { href: "/admin/users", label: "Brugere", icon: Users },
  { href: "/admin/smtp", label: "SMTP", icon: Mail, adminOnly: true },
  { href: "/admin/data", label: "Data", icon: Database },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();

  const logoutMutation = useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => {
      queryClient.clear();
      router.push("/login");
    },
  });

  return (
    <aside className="hidden md:flex w-60 flex-shrink-0 flex-col bg-slate-950 border-r border-slate-800">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-4">
        <Image
          src="/logo.png"
          alt="PricePulse"
          width={34}
          height={34}
          className="object-contain"
          priority
        />
        <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-[#29ABE2] to-[#8DC63F] bg-clip-text text-transparent">
          PricePulse
        </span>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 space-y-1 p-3">
        {mainNavItems.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                active
                  ? "bg-[#29ABE2]/15 text-[#29ABE2] ring-1 ring-[#29ABE2]/30 shadow-sm"
                  : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
              )}
            >
              <Icon className={cn("h-4 w-4", active ? "text-[#29ABE2]" : "text-slate-500")} />
              {label}
            </Link>
          );
        })}

        {/* Admin section — visible to admin and superuser */}
        {(user?.role === "admin" || user?.role === "superuser") && (
          <>
            <div className="pt-4 pb-1 px-3">
              <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                <ShieldAlert className="h-3 w-3" /> Admin
              </p>
            </div>
            {adminNavItems
              .filter((item) => !item.adminOnly || user?.role === "admin")
              .map(({ href, label, icon: Icon }) => {
              const active = pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                    active
                      ? "bg-purple-500/15 text-purple-400 ring-1 ring-purple-500/30"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
                  )}
                >
                  <Icon className={cn("h-4 w-4", active ? "text-purple-400" : "text-slate-500")} />
                  {label}
                </Link>
              );
            })}
          </>
        )}

        {/* Email preferences */}
        {user && (
          <Link
            href="/me/preferences"
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
              pathname === "/me/preferences"
                ? "bg-[#29ABE2]/15 text-[#29ABE2] ring-1 ring-[#29ABE2]/30"
                : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
            )}
          >
            <Mail className={cn("h-4 w-4", pathname === "/me/preferences" ? "text-[#29ABE2]" : "text-slate-500")} />
            Notifikationer
          </Link>
        )}
      </nav>

      {/* Footer — user info + logout */}
      <div className="border-t border-slate-800 p-3 space-y-2">
        {user && (
          <div className="flex items-center justify-between gap-2 px-1">
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-300 truncate">
                {user.display_name ?? user.email}
              </p>
              <p className="text-[10px] text-slate-600 truncate">{user.email}</p>
            </div>
            <button
              onClick={() => logoutMutation.mutate()}
              title="Log ud"
              className="flex-shrink-0 rounded-md p-1.5 text-slate-500 hover:bg-white/10 hover:text-slate-200 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
        <p className="text-xs text-slate-700 px-1">
          PricePulse {process.env.NEXT_PUBLIC_BUILD_VERSION ?? "dev"}
        </p>
      </div>
    </aside>
  );
}
