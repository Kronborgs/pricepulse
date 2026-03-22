"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuthGuard } from "@/components/layout/auth-guard";
import { User } from "@/types";
import { Loader2, UserPlus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";

export default function UsersPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<"admin" | "superuser">("superuser");
  const [error, setError] = useState<string | null>(null);
  // Per-row editing state: userId → pending timeout value (string for input)
  const [editingTimeout, setEditingTimeout] = useState<Record<string, string>>({});

  const { data: meData } = useQuery({
    queryKey: ["currentUser"],
    queryFn: () => api.auth.me(),
    staleTime: 5 * 60 * 1000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => api.adminUsers.list({ limit: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: () => api.adminUsers.create({ email, password, role, display_name: displayName || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      setShowForm(false);
      setEmail(""); setPassword(""); setDisplayName("");
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

  const users: User[] = data?.items ?? [];

  function handleDeleteUser(user: User) {
    const label = user.display_name ?? user.email;
    if (!window.confirm(`Slet bruger "${label}"?\n\nHandlingen kan ikke fortrydes.`)) return;
    deleteMutation.mutate(user.id);
  }

  return (
    <AuthGuard adminOnly>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Brugere</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Administrer systembrugere
            </p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 rounded-md bg-[#29ABE2] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#29ABE2]/90"
          >
            <UserPlus className="h-4 w-4" />
            Ny bruger
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              createMutation.mutate();
            }}
            className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-3"
          >
            <h2 className="text-sm font-semibold text-slate-200">Opret bruger</h2>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="email"
                required
                placeholder="E-mail"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
              <input
                type="text"
                placeholder="Navn (valgfrit)"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
              <input
                type="password"
                required
                minLength={8}
                placeholder="Adgangskode"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as "admin" | "superuser")}
                className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#29ABE2]"
              >
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
                {createMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Opret
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-white/5"
              >
                Annuller
              </button>
            </div>
          </form>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
          </div>
        ) : (
          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-900 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Bruger</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Rolle</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Status</th>
                  <th className="px-4 py-2.5 text-left text-xs text-slate-400 font-medium">Session-timeout</th>
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
                            : "bg-blue-500/20 text-blue-400"
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
                          {user.is_active ? "Aktiv" : "Inaktiv"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <form
                          onSubmit={(e) => {
                            e.preventDefault();
                            const mins = parseInt(pendingTimeout ?? String(currentTimeout), 10);
                            updateTimeout.mutate({ id: user.id, minutes: isNaN(mins) ? 0 : mins });
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
                              Gem
                            </button>
                          )}
                        </form>
                        {currentTimeout === 0 && pendingTimeout === undefined && (
                          <span className="text-xs text-slate-500">ingen timeout</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => toggleActive.mutate({ id: user.id, is_active: !user.is_active })}
                            className="text-xs text-slate-400 hover:text-slate-200 border border-slate-700 rounded px-2 py-1"
                          >
                            {user.is_active ? "Deaktiver" : "Aktiver"}
                          </button>
                          <button
                            onClick={() => handleDeleteUser(user)}
                            disabled={deleteMutation.isPending}
                            className="text-xs text-red-400 hover:text-red-300 border border-red-900/50 rounded px-2 py-1 flex items-center gap-1 disabled:opacity-50"
                          >
                            <Trash2 className="h-3 w-3" />
                            Slet
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}

