"use client";

import { Fragment, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  Loader2,
  Pencil,
  Shield,
  ShieldOff,
  Trash2,
  UserCheck,
  UserX,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  adminDeleteUser,
  adminGetStats,
  adminListUsers,
  adminUpdateUser,
  type AdminUser,
} from "@/lib/api";
import Navbar from "@/components/Navbar";

// ---------------------------------------------------------------------------
// Inline edit form
// ---------------------------------------------------------------------------

interface EditFormProps {
  user: AdminUser;
  onSave: (updated: AdminUser) => void;
  onCancel: () => void;
  currentUserId: string;
}

function EditForm({ user, onSave, onCancel, currentUserId }: EditFormProps) {
  const [email, setEmail] = useState(user.email);
  const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(user.is_admin);
  const [isDisabled, setIsDisabled] = useState(user.is_disabled);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {};
      if (email !== user.email) body.email = email;
      if (password) body.password = password;
      if (isAdmin !== user.is_admin) body.is_admin = isAdmin;
      if (isDisabled !== user.is_disabled) body.is_disabled = isDisabled;
      const updated = await adminUpdateUser(user.id, body);
      onSave(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Errore nel salvataggio");
    } finally {
      setSaving(false);
    }
  }

  const isSelf = user.id === currentUserId;

  return (
    <div className="flex flex-col gap-3 p-4 bg-[#111] border border-white/10 rounded-xl mt-1">
      <div className="flex gap-3">
        <div className="flex-1">
          <label className="text-xs text-zinc-400 mb-1 block">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg bg-[#1a1a1a] border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]/50"
          />
        </div>
        <div className="flex-1">
          <label className="text-xs text-zinc-400 mb-1 block">Nuova password (opzionale)</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full rounded-lg bg-[#1a1a1a] border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]/50"
          />
        </div>
      </div>
      <div className="flex items-center gap-6">
        <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={isAdmin}
            disabled={isSelf}
            onChange={(e) => setIsAdmin(e.target.checked)}
            className="accent-[#3ecf8e] w-4 h-4"
          />
          <span className={isSelf ? "text-zinc-500" : "text-zinc-300"}>Admin</span>
          {isSelf && <span className="text-xs text-zinc-600">(non modificabile su sé stessi)</span>}
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={isDisabled}
            disabled={isSelf}
            onChange={(e) => setIsDisabled(e.target.checked)}
            className="accent-red-500 w-4 h-4"
          />
          <span className={isSelf ? "text-zinc-500" : "text-zinc-300"}>Disabilitato</span>
          {isSelf && <span className="text-xs text-zinc-600">(non modificabile su sé stessi)</span>}
        </label>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 rounded-lg bg-[#3ecf8e] px-4 py-2 text-sm font-medium text-black hover:bg-[#36b87e] disabled:opacity-50 transition-colors"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
          Salva
        </button>
        <button
          onClick={onCancel}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <X size={14} />
          Annulla
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stats bar
// ---------------------------------------------------------------------------

interface Stats {
  total_users: number;
  total_analyses: number;
  analyses_by_status: Record<string, number>;
  analyses_by_provider: Record<string, number>;
}

function StatsBar({ stats }: { stats: Stats }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      {[
        { label: "Utenti", value: stats.total_users },
        { label: "Analisi", value: stats.total_analyses },
        { label: "Completate", value: stats.analyses_by_status["completed"] ?? 0 },
        { label: "Fallite", value: stats.analyses_by_status["failed"] ?? 0 },
      ].map((s) => (
        <div key={s.label} className="rounded-xl bg-[#1a1a1a] border border-white/10 p-4 text-center">
          <p className="text-2xl font-bold text-[#3ecf8e]">{s.value}</p>
          <p className="text-xs text-zinc-400 mt-1">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AdminUsersPage() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Stats | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const PAGE_SIZE = 20;

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login");
    if (!isLoading && isAuthenticated && user && !user.is_admin) router.replace("/dashboard");
  }, [isAuthenticated, isLoading, user, router]);

  async function load(p = page) {
    setLoading(true);
    try {
      const [data, s] = await Promise.all([
        adminListUsers(p, PAGE_SIZE),
        adminGetStats(),
      ]);
      setUsers(data.items);
      setTotal(data.total);
      setStats(s);
    } catch {
      // ignore — redirect will happen if not admin
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isAuthenticated && user?.is_admin) load(page);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user, page]);

  async function handleToggleDisabled(u: AdminUser) {
    setActionError(null);
    try {
      const updated = await adminUpdateUser(u.id, { is_disabled: !u.is_disabled });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Errore");
    }
  }

  async function handleDelete(id: string) {
    setActionError(null);
    try {
      await adminDeleteUser(id);
      setConfirmDelete(null);
      setUsers((prev) => prev.filter((u) => u.id !== id));
      setTotal((t) => t - 1);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Errore nella cancellazione");
    }
  }

  function handleSaved(updated: AdminUser) {
    setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    setEditingId(null);
  }

  if (isLoading || !user?.is_admin) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="animate-spin text-[#3ecf8e]" size={28} />
      </div>
    );
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="min-h-screen bg-[#0c0c0c]">
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">Gestione utenti</h1>
          <p className="text-sm text-zinc-400 mt-1">{total} utente{total !== 1 ? "i" : ""} registrat{total !== 1 ? "i" : "o"}</p>
        </div>

        {stats && <StatsBar stats={stats} />}

        {actionError && (
          <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {actionError}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="animate-spin text-[#3ecf8e]" size={28} />
          </div>
        ) : (
          <div className="rounded-xl border border-white/10 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-[#111]">
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Email</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Ruolo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Stato</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Registrato</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400 uppercase tracking-wider">Azioni</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {users.map((u) => (
                  <Fragment key={u.id}>
                    <tr
                      className={`transition-colors ${u.is_disabled ? "bg-red-950/10" : "bg-[#0c0c0c] hover:bg-[#111]"}`}
                    >
                      <td className="px-4 py-3.5">
                        <span className={u.is_disabled ? "text-zinc-500 line-through" : "text-white"}>
                          {u.email}
                        </span>
                        {u.id === user.id && (
                          <span className="ml-2 text-xs text-[#3ecf8e]">(tu)</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        {u.is_admin ? (
                          <span className="inline-flex items-center gap-1 text-[#3ecf8e] text-xs font-medium">
                            <Shield size={12} /> Admin
                          </span>
                        ) : (
                          <span className="text-zinc-500 text-xs">Utente</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        {u.is_disabled ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-medium text-red-400">
                            <UserX size={11} /> Disabilitato
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-[#3ecf8e]/10 px-2 py-0.5 text-xs font-medium text-[#3ecf8e]">
                            <UserCheck size={11} /> Attivo
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-zinc-400 text-xs">
                        {new Date(u.created_at).toLocaleDateString("it-IT")}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center justify-end gap-2">
                          {/* Toggle disabled */}
                          {u.id !== user.id && (
                            <button
                              onClick={() => handleToggleDisabled(u)}
                              title={u.is_disabled ? "Riabilita account" : "Disabilita account"}
                              className={`rounded-lg p-1.5 transition-colors ${
                                u.is_disabled
                                  ? "text-[#3ecf8e] hover:bg-[#3ecf8e]/10"
                                  : "text-zinc-400 hover:bg-white/5 hover:text-red-400"
                              }`}
                            >
                              {u.is_disabled ? <UserCheck size={15} /> : <UserX size={15} />}
                            </button>
                          )}
                          {/* Edit */}
                          <button
                            onClick={() => setEditingId(editingId === u.id ? null : u.id)}
                            title="Modifica"
                            className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/5 hover:text-white transition-colors"
                          >
                            <Pencil size={15} />
                          </button>
                          {/* Delete */}
                          {u.id !== user.id && (
                            <button
                              onClick={() => setConfirmDelete(u.id)}
                              title="Elimina"
                              className="rounded-lg p-1.5 text-zinc-400 hover:bg-red-500/10 hover:text-red-400 transition-colors"
                            >
                              <Trash2 size={15} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {editingId === u.id && (
                      <tr key={`${u.id}-edit`} className="bg-[#0c0c0c]">
                        <td colSpan={5} className="px-4 pb-4">
                          <EditForm
                            user={u}
                            currentUserId={user.id}
                            onSave={handleSaved}
                            onCancel={() => setEditingId(null)}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-6">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
                  p === page
                    ? "bg-[#3ecf8e] text-black"
                    : "border border-white/10 text-zinc-400 hover:text-white"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </main>

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-sm rounded-2xl bg-[#1a1a1a] border border-white/10 p-6">
            <h2 className="text-lg font-semibold text-white mb-2">Conferma eliminazione</h2>
            <p className="text-sm text-zinc-400 mb-6">
              Sei sicuro di voler eliminare questo utente? L&apos;operazione è irreversibile e cancellerà tutti i dati associati.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => handleDelete(confirmDelete)}
                className="flex-1 rounded-xl bg-red-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-red-600 transition-colors"
              >
                Elimina
              </button>
              <button
                onClick={() => setConfirmDelete(null)}
                className="flex-1 rounded-xl border border-white/10 px-4 py-2.5 text-sm text-zinc-400 hover:text-white transition-colors"
              >
                Annulla
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
