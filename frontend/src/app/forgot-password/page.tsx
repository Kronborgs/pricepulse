"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Loader2, CheckCircle } from "lucide-react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { t } = useI18n();

  const mutation = useMutation({
    mutationFn: () => api.auth.forgotPassword(email),
    onError: (err: Error) => setError(err.message),
  });

  if (mutation.isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="w-full max-w-sm space-y-4 p-8 rounded-xl border border-slate-800 bg-slate-900 text-center">
          <CheckCircle className="h-10 w-10 text-green-400 mx-auto" />
          <p className="text-sm text-slate-300">
            {t("forgot_password_success")}
          </p>
          <Link href="/login" className="text-xs text-[#29ABE2] hover:underline block">
            {t("forgot_password_back_to_login")}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm space-y-6 p-8 rounded-xl border border-slate-800 bg-slate-900">
        <div className="text-center space-y-1">
          <h1 className="text-xl font-bold tracking-tight text-slate-100">
            {t("forgot_password_title")}
          </h1>
          <p className="text-sm text-slate-400">
            {t("forgot_password_subtitle")}
          </p>
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
              {t("forgot_password_email_label")}
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              placeholder="din@email.dk"
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
            {t("forgot_password_submit")}
          </button>

          <Link href="/login" className="block text-center text-xs text-slate-500 hover:text-slate-300">
            {t("forgot_password_back_to_login")}
          </Link>
        </form>
      </div>
    </div>
  );
}
