"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot,
  Flag,
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useI18n, type Locale } from "@/lib/i18n";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const { t, locale, setLocale } = useI18n();

  const mainNavItems = [
    { href: "/", label: t("nav_dashboard"), icon: LayoutDashboard },
    { href: "/products", label: t("nav_products"), icon: Package },
    { href: "/settings", label: t("nav_settings"), icon: Settings },
  ];

  const adminNavItems = [
    { href: "/admin/ai-log", label: t("nav_ai_jobs"), icon: Bot },
    { href: "/admin/users", label: t("nav_users"), icon: Users },
    { href: "/admin/smtp", label: t("nav_smtp"), icon: Mail, adminOnly: true },
    { href: "/admin/data", label: t("nav_data"), icon: Database, adminOnly: true },
    { href: "/admin/reports", label: t("nav_reports"), icon: Flag },
  ];

  const logoutMutation = useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => {
      queryClient.clear();
      router.push("/login");
    },
  });

  const isPrivileged = user?.role === "admin" || user?.role === "superuser";

  const { data: unreadData } = useQuery({
    queryKey: ["reports-unread"],
    queryFn: () => api.reports.unreadCount(),
    enabled: isPrivileged,
    refetchInterval: 60_000,
  });
  const unreadCount = unreadData?.count ?? 0;

  function toggleLocale() {
    const next: Locale = locale === "en" ? "da" : "en";
    setLocale(next);
    // Persist to server if user is logged in
    if (user) {
      api.auth.updateMe({ locale: next }).catch(() => {/* silently ignore */});
      queryClient.setQueryData(["auth", "me"], { ...user, locale: next });
    }
  }

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
          const watchesActive = pathname.startsWith("/watches");
          const active =
            href === "/"
              ? pathname === "/"
              : href === "/products"
              ? pathname.startsWith("/products") || watchesActive
              : pathname.startsWith(href);
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
              const isReports = href === "/admin/reports";
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
                  {isReports && unreadCount > 0 && (
                    <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-bold text-white">
                      {unreadCount > 99 ? "99+" : unreadCount}
                    </span>
                  )}
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
            {t("nav_notifications")}
          </Link>
        )}
      </nav>

      {/* Footer — user info + lang toggle + logout */}
      <div className="border-t border-slate-800 p-3 space-y-2">
        {/* Language toggle */}
        <button
          onClick={toggleLocale}
          title={t("nav_language")}
          className="w-full flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-slate-500 hover:bg-white/5 hover:text-slate-300 transition-colors"
        >
          <span className="text-base leading-none">{locale === "en" ? "🇬🇧" : "🇩🇰"}</span>
          <span>{locale === "en" ? "English" : "Dansk"}</span>
        </button>

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
              title={t("nav_logout")}
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
