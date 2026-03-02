"use client";

import { use, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Download, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  getAnalysis, getAccessToken, streamAnalysisEvents,
  type Analysis, type DebateRound, type Verdict,
} from "@/lib/api";
import Navbar from "@/components/Navbar";
import VerdictBadge from "@/components/VerdictBadge";
import DebateRoundCard from "@/components/DebateRoundCard";
import SourceCard from "@/components/SourceCard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface StreamEvent { event: string; label: string; detail?: string; }

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [done, setDone] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/login");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated || !id) return;
    loadAnalysis();
    return () => abortRef.current?.abort();
  }, [isAuthenticated, id]);

  async function loadAnalysis() {
    const a = await getAnalysis(id);
    setAnalysis(a);
    if (a.status === "completed" || a.status === "failed") { setDone(true); return; }
    startStream(id);
  }

  async function startStream(analysisId: string) {
    setStreaming(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      for await (const { event, data } of streamAnalysisEvents(analysisId, ctrl.signal)) {
        handleSseEvent(event, data as Record<string, unknown>);
        if (event === "done" || event === "verdict") break;
      }
    } catch { /* aborted */ } finally {
      setStreaming(false);
      const final = await getAnalysis(analysisId).catch(() => null);
      if (final) setAnalysis(final);
      setDone(true);
    }
  }

  function addEvent(entry: StreamEvent) { setStreamEvents((prev) => [...prev, entry]); }

  function handleSseEvent(event: string, data: Record<string, unknown>) {
    if (event === "round_start") {
      addEvent({ event, label: `Round ${data.round} / ${data.max_rounds}` });
    } else if (event === "agent_start") {
      const labels: Record<string, string> = {
        researcher: "Researcher thinking…", devil_advocate: "Devil's Advocate thinking…", judge: "Judge evaluating…",
      };
      addEvent({ event, label: labels[data.agent as string] ?? String(data.agent) });
    } else if (event === "researcher_done") {
      addEvent({ event, label: "Researcher done", detail: `${(data.sources as unknown[])?.length ?? 0} sources` });
    } else if (event === "advocate_done") {
      addEvent({ event, label: "Devil's Advocate done", detail: `${(data.sources as unknown[])?.length ?? 0} sources` });
    } else if (event === "judge_continue") {
      addEvent({ event, label: "Judge → another round", detail: String(data.reason ?? "").slice(0, 100) });
    } else if (event === "verdict") {
      const v = data.verdict as Record<string, unknown>;
      addEvent({ event, label: `Verdict: ${v?.label}`, detail: `${Math.round((v?.confidence as number) * 100)}% confidence` });
    } else if (event === "error") {
      addEvent({ event, label: `Error: ${data.message}` });
    }
  }

  async function downloadPdf() {
    const token = getAccessToken();
    const res = await fetch(`${API}/api/v1/analysis/${id}/export`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `verdict_${id}.pdf`; a.click();
    URL.revokeObjectURL(url);
  }

  if (isLoading || !analysis) {
    return <div className="min-h-screen bg-[#0c0c0c] flex items-center justify-center"><Loader2 className="animate-spin text-zinc-600" /></div>;
  }

  const verdict = analysis.verdict as Verdict | undefined;
  const rounds = analysis.debate as DebateRound[];

  return (
    <div className="min-h-screen bg-[#0c0c0c]">
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-6">

        {/* Header */}
        <div className="flex items-start gap-3">
          <button onClick={() => router.push("/dashboard")}
            className="mt-1 p-1.5 rounded-xl text-zinc-600 hover:text-white hover:bg-white/10 transition-colors">
            <ArrowLeft size={18} />
          </button>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-zinc-500 mb-1">
              {new Date(analysis.created_at).toLocaleString()} · {analysis.llm_provider} · {analysis.llm_model}
            </p>
            <h1 className="text-lg font-semibold text-white leading-snug">
              &ldquo;{analysis.claim}&rdquo;
            </h1>
          </div>
          {done && verdict && (
            <button onClick={downloadPdf}
              className="shrink-0 flex items-center gap-1.5 rounded-xl bg-[#1a1a1a] border border-white/10 px-3 py-2 text-sm text-zinc-300 hover:bg-white/10 hover:text-white transition-colors">
              <Download size={15} />
              PDF
            </button>
          )}
        </div>

        {/* Live stream log */}
        {(streaming || streamEvents.length > 0) && !done && (
          <div className="rounded-xl bg-[#1a1a1a] border border-white/10 p-5 space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-[#3ecf8e] mb-3">
              <Loader2 size={14} className="animate-spin" />
              Analysis in progress…
            </div>
            {streamEvents.map((ev, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                  ev.event === "verdict" ? "bg-[#3ecf8e]" :
                  ev.event === "error" ? "bg-red-500" :
                  ev.event === "round_start" ? "bg-blue-500" : "bg-zinc-600"
                }`} />
                <span className="text-zinc-300">{ev.label}</span>
                {ev.detail && <span className="text-zinc-500 text-xs self-center">{ev.detail}</span>}
              </div>
            ))}
          </div>
        )}

        {/* Verdict */}
        {verdict && (
          <div className="rounded-xl bg-[#1a1a1a] border border-white/10 p-6 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <VerdictBadge label={verdict.label} confidence={verdict.confidence} size="lg" />
              <div className="text-xs text-zinc-500">
                {verdict.total_rounds} round{verdict.total_rounds !== 1 ? "s" : ""} · {(verdict.processing_time_ms / 1000).toFixed(1)}s
              </div>
            </div>
            <p className="text-zinc-300 leading-relaxed">{verdict.summary}</p>
            <details>
              <summary className="cursor-pointer text-sm font-medium text-[#3ecf8e] hover:underline list-none">
                Full reasoning ▾
              </summary>
              <p className="mt-3 text-sm text-zinc-400 whitespace-pre-wrap leading-relaxed pt-3 border-t border-white/10">
                {verdict.reasoning}
              </p>
            </details>

            {verdict.supporting_sources.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-[#3ecf8e] mb-2">Supporting sources</h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {verdict.supporting_sources.map((s, i) => <SourceCard key={i} source={s} />)}
                </div>
              </div>
            )}
            {verdict.contradicting_sources.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-red-400 mb-2">Contradicting sources</h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {verdict.contradicting_sources.map((s, i) => <SourceCard key={i} source={s} />)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {analysis.status === "failed" && (
          <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-5 py-4 text-sm text-red-400">
            Analysis failed: {analysis.error ?? "Unknown error"}
          </div>
        )}

        {/* Debate rounds */}
        {rounds.length > 0 && (
          <div>
            <h2 className="text-base font-semibold text-white mb-3">Debate transcript</h2>
            <div className="space-y-3">
              {rounds.map((r) => <DebateRoundCard key={r.round_number} round={r} />)}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
