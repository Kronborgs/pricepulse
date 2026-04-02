"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Loader2, ShieldAlert } from "lucide-react";

export default function ChangePasswordPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.auth.changePassword(oldPassword, newPassword),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
      router.push("/");
    },
    onError: (err: Error) => {
      try {
        const detail = JSON.parse(err.message.replace(/^API \d+: /, ""));
        if (Array.isArray(detail)) {
          setError(detail.map((d: { msg: string }) => d.msg).join(", "));
        } else {
          setError(typeof detail === "string" ? detail : err.message);
        }
      } catch {
        setError(err.message);
      }
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm space-y-6 p-8 rounded-xl border border-slate-800 bg-slate-900">
        <div className="text-center space-y-2">
          <ShieldAlert className="h-10 w-10 text-amber-400 mx-auto" />
          <h1 className="text-xl font-bold tracking-tight text-slate-100">
            Skift adgangskode
          </h1>
          <p className="text-sm text-slate-400">
            Din adgangskode er mere end 6 måneder gammel og skal fornyes.
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            if (newPassword !== confirm) {
              setError("De nye adgangskoder matcher ikke");
              return;
            }
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <div className="space-y-1">
            <label className="text-xs text-slate-400" htmlFor="old-password">
              Nuværende adgangskode
            </label>
            <input
              id="old-password"
              type="password"
              required
              autoComplete="current-password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs text-slate-400" htmlFor="new-password">
              Ny adgangskode
            </label>
            <input
              id="new-password"
              type="password"
              required
              autoComplete="new-password"
              minLength={10}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              placeholder="Min. 10 tegn, stort bogstav, tal og specialtegn"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs text-slate-400" htmlFor="confirm-password">
              Bekræft ny adgangskode
            </label>
            <input
              id="confirm-password"
              type="password"
              required
              autoComplete="new-password"
              minLength={10}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
            />
          </div>

          <ul className="text-xs text-slate-500 list-disc list-inside space-y-0.5">
            <li>Mindst 10 tegn</li>
            <li>Mindst ét stort bogstav (A–Z)</li>
            <li>Mindst ét tal (0–9)</li>
            <li>Mindst ét specialtegn (!@#$%^&* osv.)</li>
          </ul>

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
            Skift adgangskode
          </button>
        </form>
      </div>
    </div>
  );
}
