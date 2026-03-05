"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { List, Loader2, Plus, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  deleteAnalysis, getConfig, getOllamaModels, listAnalyses, submitAnalysis, submitBatch,
  streamAnalysisEvents, type Analysis,
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

// ---------------------------------------------------------------------------
// Verdict chart colours
// ---------------------------------------------------------------------------
const VERDICT_COLORS: Record<string, string> = {
  TRUE:          "#3ecf8e",
  FALSE:         "#ef4444",
  MISLEADING:    "#f59e0b",
  PARTIALLY_TRUE:"#f97316",
  UNVERIFIABLE:  "#71717a",
};

const VERDICT_LABELS: Record<string, string> = {
  TRUE:          "TRUE",
  FALSE:         "FALSE",
  MISLEADING:    "MISLEAD.",
  PARTIALLY_TRUE:"PARTIAL",
  UNVERIFIABLE:  "UNVERF.",
};

// ---------------------------------------------------------------------------
// Activity feed entry
// ---------------------------------------------------------------------------
interface FeedEntry {
  id: number;
  ts: string;
  msg: string;
}

let feedSeq = 0;
function makeFeedEntry(msg: string): FeedEntry {
  const now = new Date();
  const ts = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
  return { id: ++feedSeq, ts, msg };
}

// Human-readable SSE event → message
function eventToMessage(event: string, data: unknown): string | null {
  switch (event) {
    case "started":       return "Analysis started";
    case "round_start": {
      const d = data as Record<string, unknown>;
      return `Round ${d?.round ?? "?"} started`;
    }
    case "researcher":    return "Researcher thinking…";
    case "advocate":      return "Devil's advocate reviewing…";
    case "judge":         return "Judge deliberating…";
    case "round_end": {
      const d = data as Record<string, unknown>;
      return `Round ${d?.round ?? "?"} complete`;
    }
    case "done":          return "Analysis complete";
    case "error":         return "Stream error";
    default:              return null;
  }
}

// ---------------------------------------------------------------------------
// Sub-component: Verdict bar chart (pure SVG)
// ---------------------------------------------------------------------------
function VerdictBarChart({ analyses }: { analyses: Analysis[] }) {
  // Count verdicts only from completed analyses that have a verdict label
  const counts: Record<string, number> = {};
  for (const a of analyses) {
    if (a.status === "completed" && a.verdict?.label) {
      counts[a.verdict.label] = (counts[a.verdict.label] ?? 0) + 1;
    }
  }

  const entries = Object.entries(counts).filter(([, v]) => v > 0);
  // Show chart only if at least 2 distinct verdict types
  if (entries.length < 2) return null;

  const BAR_W = 36;
  const GAP   = 16;
  const MAX_H = 100;
  const LABEL_H = 36; // space for label + count below bars
  const PADDING_X = 8;
  const maxCount = Math.max(...entries.map(([, v]) => v));
  const svgW = entries.length * (BAR_W + GAP) - GAP + PADDING_X * 2;
  const svgH = MAX_H + LABEL_H + 8; // 8px top padding

  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Verdicts</span>
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        width="100%"
        style={{ maxWidth: 320, display: "block" }}
        aria-label="Verdict distribution bar chart"
      >
        {entries.map(([label, count], i) => {
          const barH = Math.max(4, Math.round((count / maxCount) * MAX_H));
          const x = PADDING_X + i * (BAR_W + GAP);
          const y = 8 + MAX_H - barH;
          const color = VERDICT_COLORS[label] ?? "#71717a";
          const shortLabel = VERDICT_LABELS[label] ?? label;
          return (
            <g key={label}>
              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={BAR_W}
                height={barH}
                rx={5}
                fill={color}
                opacity={0.85}
              />
              {/* Count above bar */}
              <text
                x={x + BAR_W / 2}
                y={y - 4}
                textAnchor="middle"
                fontSize={10}
                fontWeight="600"
                fill={color}
              >
                {count}
              </text>
              {/* Abbreviated label below bar */}
              <text
                x={x + BAR_W / 2}
                y={8 + MAX_H + 16}
                textAnchor="middle"
                fontSize={9}
                fill="#71717a"
              >
                {shortLabel}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: Live activity feed
// ---------------------------------------------------------------------------
function LiveFeed({ feed }: { feed: FeedEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed]);

  if (feed.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span
          className="inline-block w-2 h-2 rounded-full bg-blue-400"
          style={{ animation: "dashboard-pulse 1.4s ease-in-out infinite" }}
        />
        <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
          Live activity
        </span>
      </div>
      <div
        className="rounded-xl bg-[#111] border border-white/10 px-4 py-3 overflow-y-auto font-mono"
        style={{ maxHeight: 160, minHeight: 80 }}
      >
        {feed.map((entry) => (
          <div
            key={entry.id}
            style={{ animation: "dashboard-fadein 0.35s ease both" }}
            className="flex gap-2 text-xs leading-5"
          >
            <span className="text-zinc-600 shrink-0">{entry.ts}</span>
            <span className="text-zinc-300">{entry.msg}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function DashboardPage() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [total, setTotal] = useState(0);
  const [fetching, setFetching] = useState(true);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  const [claim, setClaim] = useState("");
  const [provider, setProvider] = useState<Provider>("anthropic"); // overridden by server config on mount
  const [model, setModel] = useState("");
  const [language, setLanguage] = useState("it");
  const [maxRounds, setMaxRounds] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const [showBatch, setShowBatch] = useState(false);
  const [batchClaims, setBatchClaims] = useState("");
  const [submittingBatch, setSubmittingBatch] = useState(false);
  const [batchError, setBatchError] = useState("");

  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaLoading, setOllamaLoading] = useState(false);
  const [ollamaError, setOllamaError] = useState("");
  const [sessionExpired, setSessionExpired] = useState(false);

  // Live feed
  const [feed, setFeed] = useState<FeedEntry[]>([]);
  const sseAbortRef = useRef<AbortController | null>(null);
  const sseIdRef    = useRef<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/login");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    const expired = localStorage.getItem("sessionExpired") === "true";
    if (expired) {
      setSessionExpired(true);
      localStorage.removeItem("sessionExpired");
    }
  }, []);

  useEffect(() => {
    getConfig().then(({ default_provider }) => {
      if (PROVIDERS.includes(default_provider as Provider)) {
        setProvider(default_provider as Provider);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadAnalyses(true, 1);
  }, [isAuthenticated]);

  // Reload when page changes (spinner only if list is empty)
  useEffect(() => {
    if (!isAuthenticated) return;
    loadAnalyses(analyses.length === 0, page);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  // A) Refresh when tab becomes visible again — keep current page
  useEffect(() => {
    if (!isAuthenticated) return;
    const onVisible = () => { if (document.visibilityState === "visible") loadAnalyses(false, page); };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [isAuthenticated, page]);

  // B) Poll every 8s while there are pending/running analyses — keep current page
  useEffect(() => {
    const hasRunning = analyses.some((a) => a.status === "pending" || a.status === "running");
    if (!hasRunning) return;
    const timer = setInterval(() => loadAnalyses(false, page), 8_000);
    return () => clearInterval(timer);
  }, [analyses, page]);

  // C) Live SSE feed: connect to first running analysis (one connection at a time)
  useEffect(() => {
    const runningAnalysis = analyses.find(
      (a) => a.status === "running" || a.status === "pending"
    );

    if (!runningAnalysis) {
      // No active analyses — tear down any open SSE connection
      if (sseAbortRef.current) {
        sseAbortRef.current.abort();
        sseAbortRef.current = null;
        sseIdRef.current = null;
      }
      return;
    }

    // Same analysis already being streamed — do nothing
    if (sseIdRef.current === runningAnalysis.id) return;

    // Different analysis or first time — abort previous and start fresh
    if (sseAbortRef.current) {
      sseAbortRef.current.abort();
    }
    const ctrl = new AbortController();
    sseAbortRef.current = ctrl;
    sseIdRef.current = runningAnalysis.id;

    (async () => {
      try {
        for await (const { event, data } of streamAnalysisEvents(runningAnalysis.id, ctrl.signal)) {
          const msg = eventToMessage(event, data);
          if (msg) {
            setFeed((prev) => {
              const next = [...prev, makeFeedEntry(msg)];
              return next.length > 8 ? next.slice(next.length - 8) : next;
            });
          }
        }
      } catch {
        // Aborted or network error — silently swallow
      }
    })();

    return () => {
      ctrl.abort();
      if (sseAbortRef.current === ctrl) {
        sseAbortRef.current = null;
        sseIdRef.current = null;
      }
    };
  }, [analyses]);

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

  async function loadAnalyses(showSpinner = false, pageNum = page) {
    if (showSpinner) setFetching(true);
    try {
      const res = await listAnalyses(pageNum, PAGE_SIZE);
      setAnalyses(res.items);
      setTotal(res.total);
    } finally {
      if (showSpinner) setFetching(false);
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

  async function handleBatchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBatchError("");
    const claims = batchClaims.split("\n").map((c) => c.trim()).filter(Boolean);
    if (claims.length === 0) { setBatchError("Enter at least one claim"); return; }
    if (claims.length > 10) { setBatchError("Max 10 claims per batch"); return; }
    setSubmittingBatch(true);
    try {
      const res = await submitBatch({
        claims,
        llm_provider: provider,
        llm_model: model || undefined,
        language,
        max_rounds: maxRounds,
      });
      router.push(`/batch/${res.batch_id}`);
    } catch (err: unknown) {
      setBatchError(err instanceof Error ? err.message : "Batch submission failed");
      setSubmittingBatch(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this analysis?")) return;
    await deleteAnalysis(id);
    const newList = analyses.filter((a) => a.id !== id);
    setAnalyses(newList);
    if (newList.length === 0 && page > 1) {
      setPage((p) => p - 1); // useEffect on [page] will reload
    }
  }

  // ---------------------------------------------------------------------------
  // Derived stats (no extra fetch needed)
  // ---------------------------------------------------------------------------
  const completedCount = analyses.filter((a) => a.status === "completed").length;
  const inProgressCount = analyses.filter(
    (a) => a.status === "pending" || a.status === "running"
  ).length;
  const hasRunning = inProgressCount > 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  if (isLoading) return null;

  return (
    <div className="min-h-screen bg-[#0c0c0c]">
      {/* Inject keyframe animations once */}
      <style>{`
        @keyframes dashboard-fadein {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes dashboard-pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.3; }
        }
      `}</style>

      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-8">

        {/* Disabled account banner */}
        {user?.is_disabled && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4 flex items-start gap-3">
            <span className="text-red-400 mt-0.5">⚠</span>
            <div>
              <p className="text-sm font-medium text-red-300">Account Disabled</p>
              <p className="text-xs text-red-400/80 mt-0.5">
                Your account has been disabled by an administrator. You can view previous analyses but cannot submit new requests.
              </p>
            </div>
          </div>
        )}

        {/* Session expired banner */}
        {sessionExpired && (
          <div className="rounded-xl border border-yellow-500/30 bg-yellow-500/10 px-5 py-4 flex items-center justify-between">
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
              onClick={() => {
                router.push("/login");
              }}
              className="ml-3 flex-shrink-0 rounded-lg bg-yellow-500 px-3 py-1.5 text-xs font-medium text-black hover:bg-yellow-400 transition-colors"
            >
              Log in again
            </button>
          </div>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* Overview section                                                    */}
        {/* ------------------------------------------------------------------ */}
        <section className="space-y-5">
          <h2 className="text-base font-semibold text-white">Overview</h2>

          {/* --- Stat cards --- */}
          <div className="grid grid-cols-3 gap-3">
            <StatCard
              label="Total analyses"
              value={total}
              accent="#3ecf8e"
            />
            <StatCard
              label="Completed"
              value={completedCount}
              accent="#3ecf8e"
            />
            <StatCard
              label="In progress"
              value={inProgressCount}
              accent={inProgressCount > 0 ? "#60a5fa" : "#71717a"}
              pulse={inProgressCount > 0}
            />
          </div>

          {/* --- Verdict bar chart + live feed (side by side when both present) --- */}
          {(analyses.some((a) => a.status === "completed" && a.verdict?.label) || hasRunning) && (
            <div className="flex flex-wrap gap-4">
              {/* Verdict distribution chart */}
              <div className="rounded-xl bg-[#1a1a1a] border border-white/10 p-5 flex-1 min-w-[200px]">
                <VerdictBarChart analyses={analyses} />
              </div>

              {/* Live activity feed — only when there are running/pending analyses */}
              {hasRunning && (
                <div className="rounded-xl bg-[#1a1a1a] border border-white/10 p-5 flex-1 min-w-[240px]">
                  <LiveFeed feed={feed} />
                </div>
              )}
            </div>
          )}
        </section>

        {/* ------------------------------------------------------------------ */}
        {/* New analysis                                                        */}
        {/* ------------------------------------------------------------------ */}
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

        {/* Batch submit */}
        {!user?.is_disabled && (
          <section className="rounded-xl bg-[#1a1a1a] border border-white/10 p-6">
            <button
              onClick={() => setShowBatch((v) => !v)}
              className="flex w-full items-center justify-between text-base font-semibold text-white"
            >
              <span className="flex items-center gap-2"><List size={16} className="text-[#3ecf8e]" />Batch submit</span>
              <span className="text-xs text-zinc-500">{showBatch ? "▲ hide" : "▼ expand"}</span>
            </button>
            {showBatch && (
              <form onSubmit={handleBatchSubmit} className="mt-4 space-y-4">
                <p className="text-xs text-zinc-500">One claim per line (max 10). Uses the same provider/model/language/rounds settings as above.</p>
                {batchError && (
                  <p className="rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">{batchError}</p>
                )}
                <textarea
                  required value={batchClaims}
                  onChange={(e) => setBatchClaims(e.target.value)} rows={5}
                  placeholder={"Claim one…\nClaim two…\nClaim three…"}
                  className="w-full rounded-xl bg-[#111] border border-white/10 px-4 py-3 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]/50 transition-colors resize-none font-mono"
                />
                <button type="submit" disabled={submittingBatch}
                  className="flex items-center gap-2 rounded-xl bg-[#3ecf8e] px-5 py-2 text-sm font-semibold text-black hover:bg-[#2db37a] disabled:opacity-50 transition-colors">
                  {submittingBatch ? <Loader2 size={15} className="animate-spin" /> : <List size={15} />}
                  {submittingBatch ? "Submitting…" : "Submit batch"}
                </button>
              </form>
            )}
          </section>
        )}

        {/* History */}
        <section>
          <h2 className="text-base font-semibold text-white mb-3">
            History{total > 0 && <span className="text-zinc-500 font-normal text-sm ml-2">({total} analyses)</span>}
          </h2>
          {fetching ? (
            <div className="flex justify-center py-12"><Loader2 className="animate-spin text-zinc-600" /></div>
          ) : analyses.length === 0 ? (
            <p className="text-center py-12 text-zinc-600 text-sm">No analyses yet. Submit your first claim above.</p>
          ) : (
            <>
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

              {/* Pagination controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-3 mt-4">
                  <button
                    onClick={() => setPage((p) => p - 1)}
                    disabled={page === 1}
                    className="rounded-xl bg-[#1a1a1a] border border-white/10 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    ← Precedente
                  </button>
                  <span className="text-sm text-zinc-500">
                    Pagina {page} di {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page === totalPages}
                    className="rounded-xl bg-[#1a1a1a] border border-white/10 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Successivo →
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StatCard sub-component
// ---------------------------------------------------------------------------
function StatCard({
  label,
  value,
  accent,
  pulse = false,
}: {
  label: string;
  value: number;
  accent: string;
  pulse?: boolean;
}) {
  return (
    <div className="rounded-xl bg-[#1a1a1a] border border-white/10 px-5 py-4 flex flex-col gap-1">
      <div className="flex items-center gap-2">
        {pulse && (
          <span
            className="inline-block w-2 h-2 rounded-full shrink-0"
            style={{
              background: accent,
              animation: "dashboard-pulse 1.4s ease-in-out infinite",
            }}
          />
        )}
        <span className="text-xs text-zinc-500 font-medium truncate">{label}</span>
      </div>
      <span
        className="text-3xl font-bold tabular-nums leading-none"
        style={{ color: accent }}
      >
        {value}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StatusPill sub-component
// ---------------------------------------------------------------------------
function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending:   "bg-white/10 text-zinc-400 border border-white/10",
    running:   "bg-blue-500/15 text-blue-400 border border-blue-500/30",
    completed: "bg-[#3ecf8e]/15 text-[#3ecf8e] border border-[#3ecf8e]/30",
    failed:    "bg-red-500/15 text-red-400 border border-red-500/30",
  };
  const spinning = status === "running" || status === "pending";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status] ?? styles.pending}`}>
      {spinning && <Loader2 size={11} className="animate-spin" />}
      {status}
    </span>
  );
}
