"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Eye,
  LayoutDashboard,
  Package,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/watches", label: "Watches", icon: Eye },
  { href: "/products", label: "Produkter", icon: Package },
  { href: "/settings", label: "Indstillinger", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

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

      {/* Nav */}
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map(({ href, label, icon: Icon }) => {
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
              <Icon
                className={cn(
                  "h-4 w-4",
                  active ? "text-[#29ABE2]" : "text-slate-500"
                )}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-800 p-4">
        <p className="text-xs text-slate-600">PricePulse v1.0</p>
      </div>
    </aside>
  );
}
