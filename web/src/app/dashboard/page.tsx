"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  deleteAnalysis, getConfig, getOllamaModels, listAnalyses, submitAnalysis, type Analysis,
} from "@/lib/api";
import Navbar from "@/components/Navbar";
import VerdictBadge from "@/components/VerdictBadge";

const PROVIDERS = ["anthropic", "openai", "gemini", "ollama"] as const;
type Provider = typeof PROVIDERS[number];

// Default models shown as placeholder for non-Ollama providers
const PROVIDER_DEFAULT_MODEL: Record<Provider, string> = {
  anthropic: "claude-sonnet-4-6",
  openai: "gpt-4o",
  gemini: "gemini/gemini-2.0-flash",
  ollama: "",
};

const selectCls = "rounded-xl bg-[#1a1a1a] border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]/50 transition-colors";

export default function DashboardPage() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [total, setTotal] = useState(0);
  const [fetching, setFetching] = useState(true);

  const [claim, setClaim] = useState("");
  const [provider, setProvider] = useState<Provider>("anthropic"); // overridden by server config on mount
  const [model, setModel] = useState("");
  const [language, setLanguage] = useState("it");
  const [maxRounds, setMaxRounds] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaLoading, setOllamaLoading] = useState(false);
  const [ollamaError, setOllamaError] = useState("");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/login");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    getConfig().then(({ default_provider }) => {
      if (PROVIDERS.includes(default_provider as Provider)) {
        setProvider(default_provider as Provider);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadAnalyses();
  }, [isAuthenticated]);

  // When provider changes, reset model and fetch Ollama list if needed
  useEffect(() => {
    setModel("");
    setOllamaError("");
    if (provider === "ollama") {
      fetchOllamaModels();
    }
  }, [provider]);

  async function fetchOllamaModels() {
    setOllamaLoading(true);
    setOllamaModels([]);
    try {
      const models = await getOllamaModels();
      setOllamaModels(models);
      if (models.length > 0) setModel(models[0]);
    } catch {
      setOllamaError("Ollama not reachable — is it running?");
    } finally {
      setOllamaLoading(false);
    }
  }

  async function loadAnalyses() {
    setFetching(true);
    try {
      const res = await listAnalyses();
      setAnalyses(res.items);
      setTotal(res.total);
    } finally {
      setFetching(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    setSubmitting(true);
    try {
      const res = await submitAnalysis({
        claim,
        llm_provider: provider,
        llm_model: model || undefined,
        language,
        max_rounds: maxRounds,
      });
      router.push(`/analysis/${res.analysis_id}`);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Submission failed");
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this analysis?")) return;
    await deleteAnalysis(id);
    setAnalyses((prev) => prev.filter((a) => a.id !== id));
  }

  if (isLoading) return null;

  return (
    <div className="min-h-screen bg-[#0c0c0c]">
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-8">

        {/* Disabled account banner */}
        {user?.is_disabled && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4 flex items-start gap-3">
            <span className="text-red-400 mt-0.5">⚠</span>
            <div>
              <p className="text-sm font-medium text-red-300">Account disabilitato</p>
              <p className="text-xs text-red-400/80 mt-0.5">
                Il tuo account è stato disabilitato da un amministratore. Puoi consultare le analisi precedenti ma non puoi effettuare nuove richieste.
              </p>
            </div>
          </div>
        )}

        {/* New analysis */}
        <section className={`rounded-xl bg-[#1a1a1a] border border-white/10 p-6 ${user?.is_disabled ? "opacity-50 pointer-events-none select-none" : ""}`}>
          <h2 className="text-base font-semibold text-white mb-4">Fact-check a claim</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <p className="rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">{formError}</p>
            )}
            <textarea
              required minLength={10} maxLength={2000} value={claim}
              onChange={(e) => setClaim(e.target.value)} rows={3}
              placeholder="Enter the claim or headline to fact-check…"
              className="w-full rounded-xl bg-[#111] border border-white/10 px-4 py-3 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]/50 transition-colors resize-none"
            />

            <div className="flex flex-wrap gap-3 items-end">
              {/* Provider */}
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1">Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value as Provider)}
                  className={selectCls}
                >
                  {PROVIDERS.map((p) => <option key={p} className="bg-[#1a1a1a]">{p}</option>)}
                </select>
              </div>

              {/* Model */}
              <div className="min-w-[180px]">
                <label className="block text-xs font-medium text-zinc-500 mb-1">Model</label>
                {provider === "ollama" ? (
                  ollamaLoading ? (
                    <div className={`flex items-center gap-2 ${selectCls}`}>
                      <Loader2 size={13} className="animate-spin text-zinc-500" />
                      <span className="text-zinc-500">Loading…</span>
                    </div>
                  ) : ollamaError ? (
                    <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 text-xs text-red-400">
                      {ollamaError}
                    </div>
                  ) : (
                    <select
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className={selectCls}
                    >
                      {ollamaModels.map((m) => (
                        <option key={m} value={m} className="bg-[#1a1a1a]">
                          {m.replace("ollama/", "")}
                        </option>
                      ))}
                    </select>
                  )
                ) : (
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder={PROVIDER_DEFAULT_MODEL[provider]}
                    className={selectCls + " w-full"}
                  />
                )}
              </div>

              {/* Language */}
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1">Language</label>
                <select value={language} onChange={(e) => setLanguage(e.target.value)} className={selectCls}>
                  <option value="it" className="bg-[#1a1a1a]">Italian</option>
                  <option value="en" className="bg-[#1a1a1a]">English</option>
                  <option value="fr" className="bg-[#1a1a1a]">French</option>
                  <option value="de" className="bg-[#1a1a1a]">German</option>
                  <option value="es" className="bg-[#1a1a1a]">Spanish</option>
                </select>
              </div>

              {/* Max rounds */}
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-1">Max rounds</label>
                <input type="number" min={1} max={10} value={maxRounds}
                  onChange={(e) => setMaxRounds(Number(e.target.value))}
                  className={`w-20 ${selectCls}`}
                />
              </div>

              <button type="submit" disabled={submitting || (provider === "ollama" && !model && !ollamaError)}
                className="ml-auto flex items-center gap-2 rounded-xl bg-[#3ecf8e] px-5 py-2 text-sm font-semibold text-black hover:bg-[#2db37a] disabled:opacity-50 transition-colors">
                {submitting ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
                {submitting ? "Submitting…" : "Submit"}
              </button>
            </div>
          </form>
        </section>

        {/* History */}
        <section>
          <h2 className="text-base font-semibold text-white mb-3">
            History{total > 0 && <span className="text-zinc-500 font-normal text-sm ml-2">({total})</span>}
          </h2>
          {fetching ? (
            <div className="flex justify-center py-12"><Loader2 className="animate-spin text-zinc-600" /></div>
          ) : analyses.length === 0 ? (
            <p className="text-center py-12 text-zinc-600 text-sm">No analyses yet. Submit your first claim above.</p>
          ) : (
            <div className="space-y-2">
              {analyses.map((a) => (
                <div key={a.id}
                  className="flex items-center gap-3 rounded-xl bg-[#1a1a1a] border border-white/10 px-5 py-3.5 hover:bg-white/5 transition-colors cursor-pointer"
                  onClick={() => router.push(`/analysis/${a.id}`)}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{a.claim}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">
                      {new Date(a.created_at).toLocaleString()} · {a.llm_provider} · {a.llm_model}
                    </p>
                  </div>
                  <div className="shrink-0 flex items-center gap-2">
                    {a.verdict
                      ? <VerdictBadge label={a.verdict.label} confidence={a.verdict.confidence} size="sm" />
                      : <StatusPill status={a.status} />}
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(a.id); }}
                      className="p-1 text-zinc-600 hover:text-red-400 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending:   "bg-white/10 text-zinc-400 border border-white/10",
    running:   "bg-blue-500/15 text-blue-400 border border-blue-500/30",
    completed: "bg-[#3ecf8e]/15 text-[#3ecf8e] border border-[#3ecf8e]/30",
    failed:    "bg-red-500/15 text-red-400 border border-red-500/30",
  };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status] ?? styles.pending}`}>
      {status}
    </span>
  );
}
