"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuthGuard } from "@/components/layout/auth-guard";
import { Loader2, CheckCircle, Send, Mail } from "lucide-react";
import { EmailPreferences } from "@/types";

export default function PreferencesPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["me", "email-preferences"],
    queryFn: () => api.emailPreferences.get(),
  });

  const [prefs, setPrefs] = useState<Partial<EmailPreferences>>({});
  const [saved, setSaved] = useState(false);
  const [testSent, setTestSent] = useState(false);

  useEffect(() => {
    if (data) setPrefs(data);
  }, [data]);

  const mutation = useMutation({
    mutationFn: () => api.emailPreferences.update(prefs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me", "email-preferences"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => api.emailPreferences.sendTest(),
    onSuccess: () => {
      setTestSent(true);
      setTimeout(() => setTestSent(false), 4000);
    },
  });

  function toggle(field: keyof EmailPreferences) {
    setPrefs((p) => ({ ...p, [field]: !p[field] }));
  }

  if (isLoading) {
    return (
      <AuthGuard>
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="space-y-6 max-w-lg">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Notifikationspræferencer</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Vælg hvornår og hvordan du vil modtage e-mails
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
          className="space-y-4"
        >
          {/* Hændelsesnotifikationer */}
          <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-4">
            <h2 className="text-sm font-semibold text-slate-300">Hændelsesnotifikationer</h2>
            <p className="text-xs text-slate-500 -mt-2">Sendes straks når hændelsen opstår</p>

            {[
              { field: "notify_price_drop" as const, label: "Prisfald", desc: "Modtag e-mail når prisen falder under din tærskel" },
              { field: "notify_back_in_stock" as const, label: "Tilbage på lager", desc: "Modtag e-mail når et produkt igen er på lager" },
              { field: "notify_on_change" as const, label: "Enhver ændring", desc: "Modtag e-mail ved enhver pris- eller lagerændring (uanset tærskel)" },
              { field: "notify_new_error" as const, label: "Fejl ved skanning", desc: "Modtag e-mail ved fejl i en kilde" },
            ].map(({ field, label, desc }) => (
              <label key={field} className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!(prefs as Record<string, unknown>)[field]}
                  onChange={() => toggle(field)}
                  className="mt-0.5 rounded"
                />
                <div>
                  <p className="text-sm text-slate-200">{label}</p>
                  <p className="text-xs text-slate-500">{desc}</p>
                </div>
              </label>
            ))}
          </div>

          {/* Digest */}
          <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-4">
            <h2 className="text-sm font-semibold text-slate-300">Digest-e-mail</h2>
            <p className="text-xs text-slate-500 -mt-2">Periodisk oversigt over alle ændringer i dine overvågede produkter</p>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={!!prefs.digest_enabled}
                onChange={() => toggle("digest_enabled")}
                className="rounded"
              />
              <span className="text-sm text-slate-200">Aktivér digest-e-mail</span>
            </label>

            {prefs.digest_enabled && (
              <div className="space-y-2 pl-6">
                <label className="text-xs text-slate-400 block mb-1">Frekvens</label>
                <select
                  value={prefs.digest_frequency ?? "weekly"}
                  onChange={(e) =>
                    setPrefs((p) => ({
                      ...p,
                      digest_frequency: e.target.value as EmailPreferences["digest_frequency"],
                    }))
                  }
                  className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
                >
                  <option value="hourly">Hver time</option>
                  <option value="daily">Daglig</option>
                  <option value="weekly">Ugentlig</option>
                  <option value="monthly">Månedlig</option>
                </select>

                {prefs.digest_frequency === "weekly" && (
                  <div className="pt-1">
                    <label className="text-xs text-slate-400 block mb-1">Dag</label>
                    <select
                      value={prefs.digest_day_of_week ?? 0}
                      onChange={(e) =>
                        setPrefs((p) => ({ ...p, digest_day_of_week: Number(e.target.value) }))
                      }
                      className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
                    >
                      {["Mandag","Tirsdag","Onsdag","Torsdag","Fredag","Lørdag","Søndag"].map((d, i) => (
                        <option key={i} value={i}>{d}</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Knapper */}
          <div className="flex items-center gap-3 pt-1 flex-wrap">
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90 disabled:opacity-60"
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Gem indstillinger
            </button>

            <button
              type="button"
              disabled={testMutation.isPending}
              onClick={() => testMutation.mutate()}
              className="flex items-center gap-2 rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-60"
            >
              {testMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Send test-e-mail
            </button>

            {saved && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle className="h-3 w-3" /> Gemt
              </span>
            )}
            {testMutation.isError && (
              <span className="text-xs text-red-400">
                {(testMutation.error as Error)?.message || "Fejl — er SMTP konfigureret?"}
              </span>
            )}
            {testSent && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <Mail className="h-3 w-3" /> Test-e-mail sendt til din adresse
              </span>
            )}
          </div>
        </form>

        <p className="text-xs text-muted-foreground">
          Test-e-mailen viser, hvordan en prisfald-notifikation vil se ud — med produktbillede, gammel og ny pris samt lagerstatus.
        </p>
      </div>
    </AuthGuard>
  );
}
