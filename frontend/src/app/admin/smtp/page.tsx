"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuthGuard } from "@/components/layout/auth-guard";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

export default function SMTPPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "smtp"],
    queryFn: () => api.smtp.get(),
  });

  const [host, setHost] = useState("");
  const [port, setPort] = useState("587");
  const [useTls, setUseTls] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fromEmail, setFromEmail] = useState("");
  const [fromName, setFromName] = useState("PricePulse");
  const [testEmail, setTestEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ ok: boolean; message?: string } | null>(null);

  // Pre-fill from existing settings
  const settings = data?.settings;

  const saveMutation = useMutation({
    mutationFn: () =>
      api.smtp.save({
        host: host || (settings?.host ?? ""),
        port: parseInt(port) || 587,
        use_tls: useTls,
        username: username || (settings?.username ?? ""),
        password,
        from_email: fromEmail || (settings?.from_email ?? ""),
        from_name: fromName,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "smtp"] });
      setPassword("");
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const testMutation = useMutation({
    mutationFn: () => api.smtp.test(testEmail),
    onSuccess: () => setTestResult({ ok: true }),
    onError: (err: Error) => setTestResult({ ok: false, message: err.message }),
  });

  if (isLoading) {
    return (
      <AuthGuard adminOnly>
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard adminOnly>
      <div className="space-y-6 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">SMTP-indstillinger</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Konfigurer e-mailafsendelse (adgangskoden gemmes krypteret)
          </p>
        </div>

        {data && (
          <div className={`flex items-center gap-2 text-sm rounded-md px-3 py-2 ${
            data.configured
              ? "bg-green-500/10 border border-green-500/20 text-green-400"
              : "bg-slate-500/10 border border-slate-700 text-slate-400"
          }`}>
            {data.configured
              ? <CheckCircle className="h-4 w-4" />
              : <XCircle className="h-4 w-4" />}
            {data.configured ? `Konfigureret — ${data.settings?.from_email}` : "Ikke konfigureret"}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            saveMutation.mutate();
          }}
          className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-4"
        >
          <h2 className="text-sm font-semibold text-slate-200">Server</h2>

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 space-y-1">
              <label className="text-xs text-slate-400">SMTP Host</label>
              <input
                type="text"
                placeholder={settings?.host ?? "smtp.gmail.com"}
                value={host}
                onChange={(e) => setHost(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Port</label>
              <input
                type="number"
                placeholder="587"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              id="tls"
              type="checkbox"
              checked={useTls}
              onChange={(e) => setUseTls(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="tls" className="text-xs text-slate-400">Brug STARTTLS</label>
          </div>

          <h2 className="text-sm font-semibold text-slate-200 pt-2">Afsender</h2>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Brugernavn / e-mail</label>
              <input
                type="text"
                autoComplete="off"
                placeholder={settings?.username ?? "bruger@example.com"}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Adgangskode / app-token</label>
              <input
                type="password"
                autoComplete="new-password"
                placeholder={settings ? "(lad stå tom for at beholde eksisterende)" : ""}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Afsender-e-mail</label>
              <input
                type="text"
                autoComplete="off"
                placeholder={settings?.from_email ?? "noreply@example.com"}
                value={fromEmail}
                onChange={(e) => setFromEmail(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-400">Afsendernavn</label>
              <input
                type="text"
                value={fromName}
                onChange={(e) => setFromName(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
            </div>
          </div>

          {error && (
            <p className="text-xs text-red-400 rounded-md bg-red-500/10 border border-red-500/20 px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90 disabled:opacity-60"
          >
            {saveMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Gem indstillinger
          </button>
        </form>

        {/* Test */}
        {data?.configured && (
          <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-3">
            <h2 className="text-sm font-semibold text-slate-200">Test forbindelsen</h2>
            <div className="flex gap-2">
              <input
                type="email"
                placeholder="Send test-mail til..."
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                className="flex-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
              <button
                onClick={() => { setTestResult(null); testMutation.mutate(); }}
                disabled={testMutation.isPending || !testEmail}
                className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-3 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90 disabled:opacity-60"
              >
                {testMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send test"}
              </button>
            </div>
            {testResult && (
              <p className={`text-xs flex items-center gap-1 ${testResult.ok ? "text-green-400" : "text-red-400"}`}>
                {testResult.ok
                  ? <><CheckCircle className="h-3 w-3" /> Test-mail sendt</>
                  : <><XCircle className="h-3 w-3" /> {testResult.message}</>}
              </p>
            )}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
