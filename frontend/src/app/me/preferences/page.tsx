"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuthGuard } from "@/components/layout/auth-guard";
import { Loader2, CheckCircle } from "lucide-react";
import { EmailPreferences } from "@/types";

export default function PreferencesPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["me", "email-preferences"],
    queryFn: () => api.emailPreferences.get(),
  });

  const [prefs, setPrefs] = useState<Partial<EmailPreferences>>({});
  const [saved, setSaved] = useState(false);

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
            Vælg hvornår du vil modtage e-mails
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
          className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-4"
        >
          <h2 className="text-sm font-semibold text-slate-300">Hændelser</h2>

          {[
            { field: "notify_price_drop" as const, label: "Prisfald", desc: "Modtag e-mail når prisen falder under din tærskel" },
            { field: "notify_back_in_stock" as const, label: "Tilbage på lager", desc: "Modtag e-mail når et produkt igen er på lager" },
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

          <hr className="border-slate-800" />
          <h2 className="text-sm font-semibold text-slate-300">Uge-/måneds-digest</h2>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!prefs.digest_enabled}
              onChange={() => toggle("digest_enabled")}
              className="rounded"
            />
            <span className="text-sm text-slate-200">Modtag digest-e-mail</span>
          </label>

          {prefs.digest_enabled && (
            <div className="space-y-2 pl-6">
              <label className="text-xs text-slate-400">Frekvens</label>
              <select
                value={prefs.digest_frequency ?? "weekly"}
                onChange={(e) => setPrefs((p) => ({ ...p, digest_frequency: e.target.value as EmailPreferences["digest_frequency"] }))}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              >
                <option value="daily">Daglig</option>
                <option value="weekly">Ugentlig</option>
                <option value="monthly">Månedlig</option>
              </select>
            </div>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#29ABE2]/90 disabled:opacity-60"
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Gem
            </button>
            {saved && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle className="h-3 w-3" /> Gemt
              </span>
            )}
          </div>
        </form>
      </div>
    </AuthGuard>
  );
}
