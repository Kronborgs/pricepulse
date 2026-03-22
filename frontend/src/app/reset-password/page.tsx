"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

function ResetForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.auth.resetPassword(token, password),
    onSuccess: () => router.push("/login"),
    onError: (err: Error) => setError(err.message),
  });

  if (!token) {
    return (
      <p className="text-sm text-red-400">
        Ugyldigt eller manglende nulstillingslink.{" "}
        <Link href="/forgot-password" className="underline">
          Prøv igen
        </Link>
      </p>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        if (password !== confirm) {
          setError("Adgangskoderne matcher ikke");
          return;
        }
        mutation.mutate();
      }}
      className="space-y-4"
    >
      <div className="space-y-1">
        <label className="text-xs text-slate-400" htmlFor="password">
          Ny adgangskode
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

      <div className="space-y-1">
        <label className="text-xs text-slate-400" htmlFor="confirm">
          Bekræft adgangskode
        </label>
        <input
          id="confirm"
          type="password"
          required
          minLength={8}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
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
        Skift adgangskode
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm space-y-6 p-8 rounded-xl border border-slate-800 bg-slate-900">
        <div className="text-center space-y-1">
          <h1 className="text-xl font-bold tracking-tight text-slate-100">
            Nyt kodeord
          </h1>
          <p className="text-sm text-slate-400">Vælg en ny adgangskode</p>
        </div>

        <Suspense>
          <ResetForm />
        </Suspense>
      </div>
    </div>
  );
}
