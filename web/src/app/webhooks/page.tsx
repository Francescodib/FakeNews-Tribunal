"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import {
  createWebhook,
  deleteWebhook,
  getWebhookDeliveries,
  listWebhooks,
  testWebhook,
  type Webhook,
  type WebhookDelivery,
} from "@/lib/api";
import { ChevronDown, ChevronRight, Plus, Send, Trash2 } from "lucide-react";

export default function WebhooksPage() {
  const router = useRouter();
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<Record<string, WebhookDelivery[]>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  async function load() {
    try {
      setWebhooks(await listWebhooks());
    } catch {
      setError("Failed to load webhooks");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const expired = localStorage.getItem("sessionExpired") === "true";
    if (expired) {
      setSessionExpired(true);
      localStorage.removeItem("sessionExpired");
    }
  }, []);

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await createWebhook(url.trim(), secret.trim() || undefined);
      setUrl("");
      setSecret("");
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create webhook");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this webhook?")) return;
    try {
      await deleteWebhook(id);
      await load();
    } catch {
      setError("Failed to delete webhook");
    }
  }

  async function handleTest(id: string) {
    setTestingId(id);
    try {
      await testWebhook(id);
    } catch {
      setError("Failed to send test");
    } finally {
      setTestingId(null);
    }
  }

  async function toggleExpanded(id: string) {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    if (!deliveries[id]) {
      try {
        const data = await getWebhookDeliveries(id);
        setDeliveries((prev) => ({ ...prev, [id]: data }));
      } catch {
        /* ignore */
      }
    }
  }

  const statusColor: Record<string, string> = {
    delivered: "text-[#3ecf8e]",
    failed: "text-red-400",
    pending: "text-yellow-400",
  };

  return (
    <div className="min-h-screen bg-[#0c0c0c] text-white">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-semibold">Webhooks</h1>

        {/* Session expired banner */}
        {sessionExpired && (
          <div className="mb-6 rounded-xl border border-yellow-500/30 bg-yellow-500/10 px-5 py-4 flex items-center justify-between">
            <div className="flex items-start gap-3">
              <span className="text-yellow-400 mt-0.5">⏱</span>
              <div>
                <p className="text-sm font-medium text-yellow-300">Session Expired</p>
                <p className="text-xs text-yellow-400/80 mt-0.5">
                  Your session has expired. Please log in again to continue.
                </p>
              </div>
            </div>
            <button
              onClick={() => router.push("/login")}
              className="ml-3 flex-shrink-0 rounded-lg bg-yellow-500 px-3 py-1.5 text-xs font-medium text-black hover:bg-yellow-400 transition-colors"
            >
              Log in again
            </button>
          </div>
        )}

        {/* Create form */}
        <form onSubmit={handleCreate} className="mb-8 rounded-lg border border-white/10 bg-[#1a1a1a] p-5">
          <h2 className="mb-4 text-base font-medium text-zinc-300">Add webhook</h2>
          <div className="mb-3">
            <label className="mb-1.5 block text-xs text-zinc-400">URL *</label>
            <input
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://hooks.example.com/tribunal"
              className="w-full rounded border border-white/10 bg-[#0c0c0c] px-3 py-2 text-sm focus:border-[#3ecf8e] focus:outline-none"
            />
          </div>
          <div className="mb-4">
            <label className="mb-1.5 block text-xs text-zinc-400">Secret (optional — used for HMAC signature)</label>
            <input
              type="text"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="my-secret-token"
              className="w-full rounded border border-white/10 bg-[#0c0c0c] px-3 py-2 text-sm focus:border-[#3ecf8e] focus:outline-none"
            />
          </div>
          {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={creating}
            className="flex items-center gap-2 rounded bg-[#3ecf8e] px-4 py-2 text-sm font-medium text-black hover:bg-[#36b87e] disabled:opacity-50"
          >
            <Plus size={14} />
            {creating ? "Creating…" : "Create"}
          </button>
        </form>

        {/* List */}
        {loading ? (
          <p className="text-zinc-500">Loading…</p>
        ) : webhooks.length === 0 ? (
          <p className="text-zinc-500">No webhooks yet.</p>
        ) : (
          <ul className="space-y-3">
            {webhooks.map((wh) => (
              <li key={wh.id} className="rounded-lg border border-white/10 bg-[#1a1a1a]">
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{wh.url}</p>
                    <p className="text-xs text-zinc-500">
                      {new Date(wh.created_at).toLocaleDateString()} · {wh.is_active ? "active" : "inactive"}
                    </p>
                  </div>
                  <div className="ml-3 flex items-center gap-2">
                    <button
                      onClick={() => handleTest(wh.id)}
                      disabled={testingId === wh.id}
                      title="Send test"
                      className="rounded p-1.5 text-zinc-400 hover:text-[#3ecf8e] disabled:opacity-50"
                    >
                      <Send size={14} />
                    </button>
                    <button
                      onClick={() => toggleExpanded(wh.id)}
                      title="Show deliveries"
                      className="rounded p-1.5 text-zinc-400 hover:text-white"
                    >
                      {expanded === wh.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                    <button
                      onClick={() => handleDelete(wh.id)}
                      title="Delete"
                      className="rounded p-1.5 text-zinc-400 hover:text-red-400"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Deliveries panel */}
                {expanded === wh.id && (
                  <div className="border-t border-white/10 px-4 py-3">
                    <p className="mb-2 text-xs font-medium text-zinc-400">Recent deliveries</p>
                    {!deliveries[wh.id] ? (
                      <p className="text-xs text-zinc-500">Loading…</p>
                    ) : deliveries[wh.id].length === 0 ? (
                      <p className="text-xs text-zinc-500">No deliveries yet.</p>
                    ) : (
                      <ul className="space-y-1">
                        {deliveries[wh.id].map((d) => (
                          <li key={d.id} className="flex items-center justify-between text-xs">
                            <span className="text-zinc-400">{d.event}</span>
                            <span className={statusColor[d.status] ?? "text-zinc-400"}>
                              {d.status} · {d.attempts} attempt{d.attempts !== 1 ? "s" : ""}
                            </span>
                            <span className="text-zinc-600">
                              {new Date(d.created_at).toLocaleString()}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
