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
    <aside className="hidden md:flex w-60 flex-shrink-0 flex-col border-r border-border bg-card">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-border px-4">
        <Image
          src="/logo.png"
          alt="PricePulse"
          width={32}
          height={32}
          className="rounded-md object-contain"
          priority
        />
        <span className="text-lg font-semibold tracking-tight">PricePulse</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 p-3">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border p-4">
        <p className="text-xs text-muted-foreground">PricePulse v1.0</p>
      </div>
    </aside>
  );
}
