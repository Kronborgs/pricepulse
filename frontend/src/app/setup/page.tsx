"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Check, Loader2, RotateCcw, Upload } from "lucide-react";

export default function SetupPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── create-account state ──────────────────────────────────────────────────
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);

  // ── restore-from-backup state ─────────────────────────────────────────────
  const [mode, setMode] = useState<"create" | "restore">("create");
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [restoreStats, setRestoreStats] = useState<Record<string, number> | null>(null);

  // Redirect away if setup is already done
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["auth", "setup-status"],
    queryFn: () => api.auth.setupStatus(),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.auth.setup({ email, password, display_name: displayName || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth", "setup-status"] });
      queryClient.invalidateQueries({ queryKey: ["currentUser"] });
      router.push("/");
    },
    onError: (err: Error) => setError(err.message),
  });

  const restoreMutation = useMutation({
    mutationFn: () => api.auth.setupRestore(restoreFile!),
    onSuccess: (data) => {
      setRestoreStats(data.stats);
      queryClient.invalidateQueries({ queryKey: ["auth", "setup-status"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  if (statusLoading) return null;

  if (status && !status.setup_required) {
    router.replace("/login");
    return null;
  }

  // After restore succeeds, show a "go to login" screen
  if (restoreStats) {
    const statLabels: Record<string, string> = {
      shops: "Butikker",
      products: "Produkter",
      v1_watches: "Watches (v1)",
      v1_price_history: "Prishistorik",
      v2_watches: "Watches (v2)",
      v2_watch_sources: "Kilder",
      v2_price_events: "Prisbevægelser",
      users: "Brugere",
    };
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="w-full max-w-sm space-y-6 p-8 rounded-xl border border-slate-800 bg-slate-900">
          <div className="text-center space-y-1">
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-[#29ABE2] to-[#8DC63F] bg-clip-text text-transparent">
              PricePulse
            </h1>
            <p className="text-sm text-slate-400">Backup gendannet</p>
          </div>
          <div className="rounded-md bg-green-500/10 border border-green-500/20 px-4 py-3 space-y-1.5">
            <div className="flex items-center gap-2 text-green-400 text-sm font-medium mb-2">
              <Check className="h-4 w-4" /> Gendannelse fuldført
            </div>
            {Object.entries(statLabels).map(([key, label]) =>
              restoreStats[key] !== undefined ? (
                <div key={key} className="flex justify-between text-xs text-slate-300">
                  <span className="text-slate-400">{label}</span>
                  <span>{restoreStats[key]}</span>
                </div>
              ) : null
            )}
          </div>
          <p className="text-xs text-amber-400 text-center">
            ⚠ SMTP er gendannet (deaktiveret) — genindtast kodeordet under Indstillinger → Mail.
          </p>
          <p className="text-xs text-slate-500 text-center">
            Log ind med dine tidligere oplysninger.
          </p>
          <button
            onClick={() => router.push("/login")}
            className="w-full rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90 transition-colors"
          >
            Gå til login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm space-y-6 p-8 rounded-xl border border-slate-800 bg-slate-900">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-[#29ABE2] to-[#8DC63F] bg-clip-text text-transparent">
            PricePulse
          </h1>
          <p className="text-sm text-slate-400">
            {mode === "create" ? "Opret den første admin-konto" : "Gendan fra backup"}
          </p>
        </div>

        {/* Mode toggle */}
        <div className="flex rounded-md border border-slate-700 overflow-hidden text-sm">
          <button
            onClick={() => { setMode("create"); setError(null); }}
            className={`flex-1 py-1.5 transition-colors ${mode === "create" ? "bg-slate-700 text-slate-100" : "text-slate-400 hover:text-slate-200"}`}
          >
            Ny konto
          </button>
          <button
            onClick={() => { setMode("restore"); setError(null); }}
            className={`flex-1 py-1.5 transition-colors flex items-center justify-center gap-1.5 ${mode === "restore" ? "bg-slate-700 text-slate-100" : "text-slate-400 hover:text-slate-200"}`}
          >
            <RotateCcw className="h-3.5 w-3.5" /> Gendan backup
          </button>
        </div>

        {mode === "create" ? (
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
                E-mail
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
                placeholder="admin@example.com"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-400" htmlFor="display_name">
                Navn (valgfrit)
              </label>
              <input
                id="display_name"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
                placeholder="Admin"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-400" htmlFor="password">
                Adgangskode
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
                placeholder="Minimum 8 tegn"
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
              Opret konto
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-xs text-slate-400">
              Upload en backup-fil (<code className="bg-slate-800 rounded px-1">.json.gz</code>) fra en tidligere
              installation. Dine watches, prishistorik og brugere genskabes.
            </p>

            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".gz"
                className="hidden"
                onChange={(e) => setRestoreFile(e.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full flex items-center justify-center gap-2 rounded-md border border-dashed border-slate-600 bg-slate-800/50 px-4 py-3 text-sm text-slate-400 hover:border-slate-500 hover:text-slate-300 transition-colors"
              >
                <Upload className="h-4 w-4" />
                {restoreFile ? restoreFile.name : "Vælg backup-fil…"}
              </button>
            </div>

            {error && (
              <p className="text-xs text-red-400 rounded-md bg-red-500/10 border border-red-500/20 px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="button"
              disabled={!restoreFile || restoreMutation.isPending}
              onClick={() => { setError(null); restoreMutation.mutate(); }}
              className="w-full flex items-center justify-center gap-2 rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90 disabled:opacity-60 transition-colors"
            >
              {restoreMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
              Gendan backup
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

