"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { getBatch, type BatchStatus } from "@/lib/api";

export default function BatchPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [batch, setBatch] = useState<BatchStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  async function load() {
    try {
      setBatch(await getBatch(id));
    } catch {
      setError("Batch not found");
    }
  }

  useEffect(() => {
    const expired = localStorage.getItem("sessionExpired") === "true";
    if (expired) {
      setSessionExpired(true);
      localStorage.removeItem("sessionExpired");
    }
  }, []);

  useEffect(() => {
    load();
    // Poll while running
    const interval = setInterval(() => {
      if (batch?.status === "completed" || batch?.status === "partially_failed") {
        clearInterval(interval);
        return;
      }
      load();
    }, 3000);
    return () => clearInterval(interval);
  }, [id, batch?.status]);

  const statusColor: Record<string, string> = {
    pending: "text-yellow-400",
    running: "text-blue-400",
    completed: "text-[#3ecf8e]",
    partially_failed: "text-orange-400",
  };

  if (error) {
    return (
      <div className="min-h-screen bg-[#0c0c0c] text-white">
        <Navbar />
        <main className="mx-auto max-w-3xl px-4 py-8">
          {sessionExpired && (
            <div className="mb-6 rounded-xl border border-yellow-500/30 bg-yellow-500/10 px-5 py-4 flex items-center justify-between">
              <div className="flex items-start gap-3">
                <span className="text-yellow-400 mt-0.5">⏱</span>
                <div>
                  <p className="text-sm font-medium text-yellow-300">Sessione scaduta</p>
                  <p className="text-xs text-yellow-400/80 mt-0.5">
                    Il tuo token è scaduto. Esegui di nuovo l'accesso per continuare.
                  </p>
                </div>
              </div>
              <button
                onClick={() => router.push("/login")}
                className="ml-3 flex-shrink-0 rounded-lg bg-yellow-500 px-3 py-1.5 text-xs font-medium text-black hover:bg-yellow-400 transition-colors"
              >
                Login di nuovo
              </button>
            </div>
          )}
          <p className="text-red-400">{error}</p>
        </main>
      </div>
    );
  }

  if (!batch) {
    return (
      <div className="min-h-screen bg-[#0c0c0c] text-white">
        <Navbar />
        <main className="mx-auto max-w-3xl px-4 py-8">
          {sessionExpired && (
            <div className="mb-6 rounded-xl border border-yellow-500/30 bg-yellow-500/10 px-5 py-4 flex items-center justify-between">
              <div className="flex items-start gap-3">
                <span className="text-yellow-400 mt-0.5">⏱</span>
                <div>
                  <p className="text-sm font-medium text-yellow-300">Sessione scaduta</p>
                  <p className="text-xs text-yellow-400/80 mt-0.5">
                    Il tuo token è scaduto. Esegui di nuovo l'accesso per continuare.
                  </p>
                </div>
              </div>
              <button
                onClick={() => router.push("/login")}
                className="ml-3 flex-shrink-0 rounded-lg bg-yellow-500 px-3 py-1.5 text-xs font-medium text-black hover:bg-yellow-400 transition-colors"
              >
                Login di nuovo
              </button>
            </div>
          )}
          <p className="text-zinc-400">Loading…</p>
        </main>
      </div>
    );
  }

  const progress = batch.total > 0 ? ((batch.completed + batch.failed) / batch.total) * 100 : 0;

  return (
    <div className="min-h-screen bg-[#0c0c0c] text-white">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-8">
        {sessionExpired && (
          <div className="mb-6 rounded-xl border border-yellow-500/30 bg-yellow-500/10 px-5 py-4 flex items-center justify-between">
            <div className="flex items-start gap-3">
              <span className="text-yellow-400 mt-0.5">⏱</span>
              <div>
                <p className="text-sm font-medium text-yellow-300">Sessione scaduta</p>
                <p className="text-xs text-yellow-400/80 mt-0.5">
                  Il tuo token è scaduto. Esegui di nuovo l'accesso per continuare.
                </p>
              </div>
            </div>
            <button
              onClick={() => router.push("/login")}
              className="ml-3 flex-shrink-0 rounded-lg bg-yellow-500 px-3 py-1.5 text-xs font-medium text-black hover:bg-yellow-400 transition-colors"
            >
              Login di nuovo
            </button>
          </div>
        )}
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Batch</h1>
          <span className={`text-sm font-medium ${statusColor[batch.status] ?? "text-zinc-400"}`}>
            {batch.status}
          </span>
        </div>

        {/* Progress bar */}
        <div className="mb-6 rounded-lg border border-white/10 bg-[#1a1a1a] p-5">
          <div className="mb-2 flex justify-between text-sm text-zinc-400">
            <span>{batch.completed} completed · {batch.failed} failed</span>
            <span>{batch.completed + batch.failed} / {batch.total}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-[#3ecf8e] transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2 text-xs text-zinc-500">
            Created {new Date(batch.created_at).toLocaleString()}
            {batch.completed_at && ` · Completed ${new Date(batch.completed_at).toLocaleString()}`}
          </div>
        </div>

        {/* Analysis list */}
        <h2 className="mb-3 text-base font-medium text-zinc-300">Analyses</h2>
        {batch.analysis_ids.length === 0 ? (
          <p className="text-zinc-500 text-sm">No analyses yet.</p>
        ) : (
          <ul className="space-y-2">
            {batch.analysis_ids.map((aid) => (
              <li key={aid}>
                <Link
                  href={`/analysis/${aid}`}
                  className="block rounded-lg border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-zinc-300 hover:border-[#3ecf8e]/40 hover:text-white transition-colors"
                >
                  {aid}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
