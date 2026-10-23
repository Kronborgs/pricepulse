"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuthGuard } from "@/components/layout/auth-guard";
import { User } from "@/types";
import { Loader2, UserPlus, Trash2, Mail, MonitorPlay, KeyRound, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/lib/i18n";

export default function UsersPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<"admin" | "superuser" | "user">("superuser");
  const [error, setError] = useState<string | null>(null);
  const [inviteSent, setInviteSent] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [passwordUser, setPasswordUser] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  // Per-row editing state: userId → pending timeout value (string for input)
  const [editingTimeout, setEditingTimeout] = useState<Record<string, string>>({});

  const { data: meData } = useQuery({
    queryKey: ["currentUser"],
    queryFn: () => api.auth.me(),
    staleTime: 5 * 60 * 1000,
  });

  const { data, isLoading, error: listError } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => api.adminUsers.list({ limit: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: () => api.adminUsers.create({ email, role, display_name: displayName || undefined }),
    onSuccess: (_data, _vars) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      setShowForm(false);
      setEmail(""); setDisplayName("");
      setInviteSent(email);
      setTimeout(() => setInviteSent(null), 6000);
    },
    onError: (err: Error) => setError(err.message),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.adminUsers.update(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  const updateTimeout = useMutation({
    mutationFn: ({ id, minutes }: { id: string; minutes: number }) =>
      api.adminUsers.update(id, { session_timeout_minutes: minutes }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      setEditingTimeout((prev) => { const n = { ...prev }; delete n[variables.id]; return n; });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.adminUsers.delete(id),
    onSuccess: (_data, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      // Hvis vi slettede os selv → gå til setup (systemet vender tilbage til first-run state)
      if (meData?.id === deletedId) {
        queryClient.clear();
        router.push("/setup");
      }
    },
  });

  const resendResetMutation = useMutation({
    mutationFn: (user: User) => api.adminUsers.resendResetLink(user.id),
    onSuccess: (_result, user) => {
      setActionError(null);
      setStatusMessage(`Reset link sent to ${user.email}`);
      setTimeout(() => setStatusMessage(null), 6000);
    },
    onError: (err: Error) => {
      setStatusMessage(null);
      setActionError(err.message);
    },
  });

  const setPasswordMutation = useMutation({
    mutationFn: () => api.adminUsers.setPassword(passwordUser!.id, newPassword),
    onSuccess: () => {
      setPasswordUser(null);
      setNewPassword("");
      setConfirmPassword("");
      setPasswordError(null);
      setStatusMessage("Password updated. The user will need to sign in again.");
      setTimeout(() => setStatusMessage(null), 6000);
    },
    onError: (err: Error) => setPasswordError(err.message),
  });

  const users: User[] = data?.items ?? [];

  function handleDeleteUser(user: User) {
    const label = user.display_name ?? user.email;
    if (!window.confirm(`Delete user "${label}"?\n\nThis action cannot be undone.`)) return;
    deleteMutation.mutate(user.id);
  }

  function openUserWatches(userId: string) {
    try { localStorage.setItem("watches_owner_filter", JSON.stringify([userId])); } catch { /* ignore */ }
    router.push("/watches");
  }

  return (
    <AuthGuard adminOnly superuserAllowed>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{t("admin_users_title")}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {t("admin_users_subtitle")}
            </p>
          </div>
          <button
            onClick={() => { setShowForm(!showForm); setError(null); }}
            className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#29ABE2]/90"
          >
            <UserPlus className="h-4 w-4" />
            {t("admin_users_new")}
          </button>
        </div>

        {inviteSent && (
          <div className="flex items-center gap-2 rounded-md bg-green-500/10 border border-green-500/20 px-4 py-3 text-sm text-green-400">
            <Mail className="h-4 w-4 shrink-0" />
            Invitation sent to <strong>{inviteSent}</strong>
          </div>
        )}

        {statusMessage && (
          <output className="block rounded-md border border-green-500/20 bg-green-500/10 px-4 py-3 text-sm text-green-300">
            {statusMessage}
          </output>
        )}
        {actionError && (
          <div role="alert" className="rounded-md border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {actionError}
          </div>
        )}

        {showForm && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              createMutation.mutate();
            }}
            className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-3"
          >
            <h2 className="text-sm font-semibold text-slate-200">Create user</h2>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="email"
                required
                placeholder={t("admin_users_email")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
              <input
                type="text"
                placeholder={t("admin_users_name")}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as "admin" | "superuser" | "user")}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              >
                <option value="user">User</option>
                <option value="superuser">Superuser</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            {error && (
              <p className="text-xs text-red-400">{error}</p>
            )}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#29ABE2]/90 disabled:opacity-60"
              >
                {createMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Mail className="h-3 w-3" />}
                Send invitation
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-white hover:bg-white/5"
              >
                {t("settings_cancel")}
              </button>
            </div>
          </form>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
          </div>
        ) : listError ? (
          <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-sm text-red-400">
            Failed to fetch user list: {(listError as Error).message}
          </div>
        ) : (
          <>
          <div className="hidden md:block rounded-lg border border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead className="bg-slate-900 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">User</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">{t("admin_users_role")}</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">{t("admin_users_status")}</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">{t("admin_users_session_timeout")}</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {users.map((user) => {
                  const pendingTimeout = editingTimeout[user.id];
                  const currentTimeout = user.session_timeout_minutes ?? 0;
                  return (
                    <tr key={user.id} className="hover:bg-white/5">
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-200">
                          {user.display_name ?? user.email}
                        </div>
                        {user.display_name && (
                          <div className="text-xs text-slate-500">{user.email}</div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          user.role === "admin"
                            ? "bg-purple-500/20 text-purple-400"
                            : user.role === "superuser"
                            ? "bg-blue-500/20 text-blue-400"
                            : "bg-slate-500/20 text-slate-400"
                        }`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          user.is_active
                            ? "bg-green-500/20 text-green-400"
                            : "bg-slate-500/20 text-slate-400"
                        }`}>
                          {user.is_active ? t("admin_users_active") : t("admin_users_inactive")}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <form
                          onSubmit={(e) => {
                            e.preventDefault();
                            const mins = Number.parseInt(pendingTimeout ?? String(currentTimeout), 10);
                            updateTimeout.mutate({ id: user.id, minutes: Number.isNaN(mins) ? 0 : mins });
                          }}
                          className="flex items-center gap-1"
                        >
                          <input
                            type="number"
                            min={0}
                            max={1440}
                            placeholder="0"
                            value={pendingTimeout ?? String(currentTimeout)}
                            onChange={(e) =>
                              setEditingTimeout((prev) => ({ ...prev, [user.id]: e.target.value }))
                            }
                            className="w-20 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
                          />
                          <span className="text-xs text-slate-500">min</span>
                          {pendingTimeout !== undefined && (
                            <button
                              type="submit"
                              disabled={updateTimeout.isPending}
                              className="text-xs text-[#29ABE2] hover:text-[#29ABE2]/80 ml-1"
                            >
                              {t("admin_users_save")}
                            </button>
                          )}
                        </form>
                        {currentTimeout === 0 && pendingTimeout === undefined && (
                          <span className="text-xs text-slate-500">no timeout</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openUserWatches(user.id)}
                            title="View user watches"
                            className="text-xs text-slate-400 hover:text-[#29ABE2] border border-slate-700 rounded px-2 py-1 flex items-center gap-1"
                          >
                            <MonitorPlay className="h-3 w-3" />
                            Watches
                          </button>
                          <button
                            onClick={() => { setActionError(null); resendResetMutation.mutate(user); }}
                            disabled={!user.is_active || resendResetMutation.isPending}
                            title="Send password reset link"
                            className="text-xs text-slate-400 hover:text-[#29ABE2] border border-slate-700 rounded px-2 py-1 flex items-center gap-1 disabled:opacity-50"
                          >
                            {resendResetMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Mail className="h-3 w-3" />}
                            Reset link
                          </button>
                          <button
                            onClick={() => { setPasswordUser(user); setPasswordError(null); setNewPassword(""); setConfirmPassword(""); }}
                            title="Set a temporary password"
                            className="text-xs text-slate-400 hover:text-[#29ABE2] border border-slate-700 rounded px-2 py-1 flex items-center gap-1"
                          >
                            <KeyRound className="h-3 w-3" />
                            Set password
                          </button>
                          {/* Superuser må ikke deaktivere admin/superuser-brugere */}
                          {!(meData?.role === "superuser" && user.role !== "user") && (
                          <button
                            onClick={() => toggleActive.mutate({ id: user.id, is_active: !user.is_active })}
                            className="text-xs text-slate-400 hover:text-slate-200 border border-slate-700 rounded px-2 py-1"
                          >
                            {user.is_active ? t("admin_users_deactivate") : t("admin_users_activate")}
                          </button>
                          )}
                          {/* Superuser må ikke slette admin-brugere */}
                          {!(meData?.role === "superuser" && user.role !== "user") && (
                          <button
                            onClick={() => handleDeleteUser(user)}
                            disabled={deleteMutation.isPending}
                            className="text-xs text-red-400 hover:text-red-300 border border-red-900/50 rounded px-2 py-1 flex items-center gap-1 disabled:opacity-50"
                          >
                            <Trash2 className="h-3 w-3" />
                            {t("admin_users_delete")}
                          </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            </div>
          </div>
          <div className="space-y-3 md:hidden">
            {users.map((user) => (
              <section key={user.id} className="space-y-3 rounded-md border border-slate-800 bg-slate-900 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-all font-medium text-slate-100">{user.display_name ?? user.email}</p>
                    {user.display_name && <p className="break-all text-xs text-slate-400">{user.email}</p>}
                  </div>
                  <span className={`shrink-0 rounded px-2 py-1 text-xs ${user.is_active ? "bg-green-500/15 text-green-300" : "bg-slate-700 text-slate-300"}`}>
                    {user.is_active ? t("admin_users_active") : t("admin_users_inactive")}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-slate-300">{user.role}</span>
                  <label className="flex items-center gap-2 text-slate-400">
                    <span>Timeout</span>
                    <input
                      type="number"
                      min={0}
                      max={1440}
                      aria-label={`Session timeout for ${user.email}`}
                      value={editingTimeout[user.id] ?? String(user.session_timeout_minutes ?? 0)}
                      onChange={(event) => setEditingTimeout((prev) => ({ ...prev, [user.id]: event.target.value }))}
                      onBlur={(event) => {
                        const mins = Number.parseInt(event.target.value, 10);
                        if (editingTimeout[user.id] !== undefined) updateTimeout.mutate({ id: user.id, minutes: Number.isNaN(mins) ? 0 : mins });
                      }}
                      className="w-16 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-100"
                    />
                    <span>min</span>
                  </label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => openUserWatches(user.id)}
                    className="flex min-h-10 items-center justify-center gap-2 rounded border border-slate-700 px-2 text-xs text-slate-300"
                  >
                    <MonitorPlay className="h-4 w-4" /> Watches
                  </button>
                  <button
                    onClick={() => { setActionError(null); resendResetMutation.mutate(user); }}
                    disabled={!user.is_active || resendResetMutation.isPending}
                    className="flex min-h-10 items-center justify-center gap-2 rounded border border-slate-700 px-2 text-xs text-slate-300 disabled:opacity-50"
                  >
                    <Mail className="h-4 w-4" /> Reset link
                  </button>
                  <button
                    onClick={() => { setPasswordUser(user); setPasswordError(null); setNewPassword(""); setConfirmPassword(""); }}
                    className="flex min-h-10 items-center justify-center gap-2 rounded border border-slate-700 px-2 text-xs text-slate-300"
                  >
                    <KeyRound className="h-4 w-4" /> Set password
                  </button>
                  {!(meData?.role === "superuser" && user.role !== "user") && (
                    <button
                      onClick={() => toggleActive.mutate({ id: user.id, is_active: !user.is_active })}
                      className="min-h-10 rounded border border-slate-700 px-2 text-xs text-slate-300"
                    >
                      {user.is_active ? t("admin_users_deactivate") : t("admin_users_activate")}
                    </button>
                  )}
                  {!(meData?.role === "superuser" && user.role !== "user") && (
                    <button
                      onClick={() => handleDeleteUser(user)}
                      disabled={deleteMutation.isPending}
                      className="col-span-2 flex min-h-10 items-center justify-center gap-2 rounded border border-red-900/50 px-2 text-xs text-red-400 disabled:opacity-50"
                    >
                      <Trash2 className="h-4 w-4" /> {t("admin_users_delete")}
                    </button>
                  )}
                </div>
              </section>
            ))}
          </div>
          </>
        )}

        {passwordUser && (
          <dialog
            open
            aria-labelledby="admin-password-title"
            className="fixed inset-0 z-50 m-0 flex h-full w-full max-w-none items-center justify-center border-0 bg-black/70 p-4"
          >
            <form
              onSubmit={(event) => {
                event.preventDefault();
                setPasswordError(null);
                if (newPassword !== confirmPassword) {
                  setPasswordError("Passwords do not match.");
                  return;
                }
                setPasswordMutation.mutate();
              }}
              className="w-full max-w-md space-y-4 rounded-lg border border-slate-700 bg-slate-900 p-5 shadow-xl"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 id="admin-password-title" className="text-base font-semibold text-slate-100">Set user password</h2>
                  <p className="mt-1 break-all text-sm text-slate-400">{passwordUser.email}</p>
                </div>
                <button type="button" onClick={() => setPasswordUser(null)} aria-label="Close" className="rounded p-2 text-slate-400 hover:bg-white/5 hover:text-white">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <input
                type="password"
                required
                minLength={10}
                autoComplete="new-password"
                aria-label="New password"
                placeholder="New password (10+ characters)"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
              <input
                type="password"
                required
                minLength={10}
                autoComplete="new-password"
                aria-label="Confirm new password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
              <p className="text-xs text-slate-400">Must include an uppercase letter, a number, and a special character.</p>
              {passwordError && <p role="alert" className="text-sm text-red-400">{passwordError}</p>}
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => setPasswordUser(null)} className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-white/5">Cancel</button>
                <button type="submit" disabled={setPasswordMutation.isPending} className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-3 py-2 text-sm font-medium text-white disabled:opacity-60">
                  {setPasswordMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Set password
                </button>
              </div>
            </form>
          </dialog>
        )}
      </div>
    </AuthGuard>
  );
}

