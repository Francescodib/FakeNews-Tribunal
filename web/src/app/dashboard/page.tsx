"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { deleteAnalysis, listAnalyses, submitAnalysis, type Analysis } from "@/lib/api";
import Navbar from "@/components/Navbar";
import VerdictBadge from "@/components/VerdictBadge";

const PROVIDERS = ["anthropic", "openai", "gemini", "ollama"] as const;
const selectCls = "rounded-xl bg-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors";

export default function DashboardPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [total, setTotal] = useState(0);
  const [fetching, setFetching] = useState(true);

  const [claim, setClaim] = useState("");
  const [provider, setProvider] = useState("anthropic");
  const [language, setLanguage] = useState("it");
  const [maxRounds, setMaxRounds] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/login");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadAnalyses();
  }, [isAuthenticated]);

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
      const res = await submitAnalysis({ claim, llm_provider: provider, language, max_rounds: maxRounds });
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
    <div className="min-h-screen bg-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-8">

        {/* New analysis */}
        <section className="rounded-2xl bg-white shadow-sm p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Fact-check a claim</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</p>
            )}
            <textarea
              required minLength={10} maxLength={2000} value={claim}
              onChange={(e) => setClaim(e.target.value)} rows={3}
              placeholder="Enter the claim or headline to fact-check…"
              className="w-full rounded-xl bg-slate-100 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors resize-none"
            />
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Provider</label>
                <select value={provider} onChange={(e) => setProvider(e.target.value)} className={selectCls}>
                  {PROVIDERS.map((p) => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Language</label>
                <select value={language} onChange={(e) => setLanguage(e.target.value)} className={selectCls}>
                  <option value="it">Italian</option>
                  <option value="en">English</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="es">Spanish</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Max rounds</label>
                <input type="number" min={1} max={10} value={maxRounds}
                  onChange={(e) => setMaxRounds(Number(e.target.value))}
                  className={`w-20 ${selectCls}`}
                />
              </div>
              <button type="submit" disabled={submitting}
                className="ml-auto flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
                {submitting ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
                {submitting ? "Submitting…" : "Submit"}
              </button>
            </div>
          </form>
        </section>

        {/* History */}
        <section>
          <h2 className="text-lg font-semibold text-slate-900 mb-3">
            History{total > 0 && <span className="text-slate-400 font-normal text-sm ml-2">({total})</span>}
          </h2>
          {fetching ? (
            <div className="flex justify-center py-12"><Loader2 className="animate-spin text-slate-400" /></div>
          ) : analyses.length === 0 ? (
            <p className="text-center py-12 text-slate-400 text-sm">No analyses yet. Submit your first claim above.</p>
          ) : (
            <div className="space-y-2">
              {analyses.map((a) => (
                <div key={a.id}
                  className="flex items-center gap-3 rounded-2xl bg-white shadow-sm px-5 py-3.5 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => router.push(`/analysis/${a.id}`)}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{a.claim}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {new Date(a.created_at).toLocaleString()} · {a.llm_provider}
                    </p>
                  </div>
                  <div className="shrink-0 flex items-center gap-2">
                    {a.verdict
                      ? <VerdictBadge label={a.verdict.label} confidence={a.verdict.confidence} size="sm" />
                      : <StatusPill status={a.status} />}
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(a.id); }}
                      className="p-1 text-slate-300 hover:text-red-500 transition-colors">
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
    pending:   "bg-slate-100 text-slate-600",
    running:   "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed:    "bg-red-100 text-red-700",
  };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status] ?? styles.pending}`}>
      {status}
    </span>
  );
}
