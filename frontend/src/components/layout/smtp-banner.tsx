"use client";

import Link from "next/link";
import { ArrowRight, MailX, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export function SmtpBanner() {
  const [dismissed, setDismissed] = useState(false);
  const { data: user } = useCurrentUser();

  const { data: smtp } = useQuery({
    queryKey: ["admin", "smtp"],
    queryFn: () => api.smtp.get(),
    enabled: user?.role === "admin",
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  if (dismissed) return null;
  if (user?.role !== "admin") return null;
  if (!smtp || smtp.configured) return null;

  return (
    <div className="flex items-center gap-3 border-b border-amber-500/20 bg-amber-500/[0.06] px-5 py-2.5">
      {/* Icon pill */}
      <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-amber-500/15 ring-1 ring-amber-500/25">
        <MailX className="h-3.5 w-3.5 text-amber-400" />
      </div>

      {/* Text */}
      <div className="flex flex-1 items-center gap-2 min-w-0">
        <span className="text-xs font-semibold text-amber-300">
          SMTP ikke konfigureret
        </span>
        <span className="hidden sm:block text-xs text-amber-600">·</span>
        <span className="hidden sm:block text-xs text-amber-500/70 truncate">
          E-mail notifikationer er slået fra indtil SMTP opsættes
        </span>
      </div>

      {/* CTA */}
      <Link
        href="/admin/smtp"
        className="flex flex-shrink-0 items-center gap-1.5 rounded-md bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-300 ring-1 ring-amber-500/30 transition-all hover:bg-amber-500/25 hover:text-amber-200"
      >
        Opsæt SMTP
        <ArrowRight className="h-3 w-3" />
      </Link>

      {/* Dismiss */}
      <button
        onClick={() => setDismissed(true)}
        title="Skjul advarsel"
        className="flex-shrink-0 rounded-md p-1 text-amber-700 transition-colors hover:bg-amber-500/15 hover:text-amber-400"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
