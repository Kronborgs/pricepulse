"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";

export default function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: setupStatus, isLoading: setupLoading } = useQuery({
    queryKey: ["auth", "setup-status"],
    queryFn: () => api.auth.setupStatus(),
    staleTime: 60_000,
    retry: false,
  });

  useEffect(() => {
    if (!setupLoading && setupStatus?.setup_required) {
      router.replace("/setup");
    }
  }, [setupLoading, setupStatus, router]);

  const mutation = useMutation({
    mutationFn: () => api.auth.login({ email, password }),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
      if (user.must_change_password) {
        router.push("/change-password");
      } else {
        router.push("/");
      }
    },
    onError: (err: Error) => {
      setError(err.message.includes("401") ? t("login_error") : err.message);
    },
  });

  // Vis ingenting mens vi tjekker om setup er nødvendig
  if (setupLoading || setupStatus?.setup_required) return null;

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm space-y-6 p-8 rounded-xl border border-slate-800 bg-slate-900">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-[#29ABE2] to-[#8DC63F] bg-clip-text text-transparent">
            PricePulse
          </h1>
          <p className="text-sm text-slate-400">{t("login_heading")}</p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <div className="space-y-1">
            <label className="text-xs text-slate-400" htmlFor="email">
              {t("login_email")}
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              placeholder="din@email.dk"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-xs text-slate-400" htmlFor="password">
                {t("login_password")}
              </label>
              <Link
                href="/forgot-password"
                className="text-xs text-[#29ABE2] hover:underline"
              >
                {t("login_forgot_password")}
              </Link>
            </div>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
            />
          </div>

          {error && (
            <p className="text-xs text-red-400 rounded-md bg-red-500/10 border border-red-500/20 px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full flex items-center justify-center gap-2 rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90 disabled:opacity-60 transition-colors"
          >
            {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            {t("login_submit")}
          </button>
        </form>
      </div>
    </div>
  );
}
