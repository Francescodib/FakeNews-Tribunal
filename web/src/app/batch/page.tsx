"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { listBatches, type BatchStatus } from "@/lib/api";
import Navbar from "@/components/Navbar";

export default function BatchListPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  const [batches, setBatches] = useState<BatchStatus[]>([]);
  const [total, setTotal] = useState(0);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/login");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadBatches(true);
  }, [isAuthenticated]);

  // Refresh when tab becomes visible again
  useEffect(() => {
    if (!isAuthenticated) return;
    const onVisible = () => {
      if (document.visibilityState === "visible") loadBatches();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [isAuthenticated]);

  // Poll every 8s while there are pending/running batches
  useEffect(() => {
    const hasRunning = batches.some(
      (b) => b.status === "pending" || b.status === "running"
    );
    if (!hasRunning) return;
    const timer = setInterval(loadBatches, 8_000);
    return () => clearInterval(timer);
  }, [batches]);

  async function loadBatches(showSpinner = false) {
    if (showSpinner) setFetching(true);
    try {
      const res = await listBatches();
      setBatches(res.items);
      setTotal(res.total);
    } finally {
      if (showSpinner) setFetching(false);
    }
  }

  if (isLoading) return null;

  return (
    <div className="min-h-screen bg-[#0c0c0c]">
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-6">
        <h1 className="text-xl font-semibold text-white">
          Batch{total > 0 && (
            <span className="text-zinc-500 font-normal text-sm ml-2">({total})</span>
          )}
        </h1>

        {fetching ? (
          <div className="flex justify-center py-12">
            <Loader2 className="animate-spin text-zinc-600" />
          </div>
        ) : batches.length === 0 ? (
          <p className="text-center py-12 text-zinc-600 text-sm">
            No batches yet. Submit a batch from the dashboard.
          </p>
        ) : (
          <div className="space-y-2">
            {batches.map((b) => (
              <div
                key={b.id}
                onClick={() => router.push(`/batch/${b.id}`)}
                className="flex items-center gap-4 rounded-xl bg-[#1a1a1a] border border-white/10 px-5 py-4 hover:bg-white/5 transition-colors cursor-pointer"
              >
                {/* Date + ID */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-zinc-500 font-mono truncate">{b.id}</p>
                  <p className="text-xs text-zinc-600 mt-0.5">
                    {new Date(b.created_at).toLocaleString()}
                    {b.completed_at &&
                      ` · completed ${new Date(b.completed_at).toLocaleString()}`}
                  </p>
                </div>

                {/* Claim counters */}
                <div className="shrink-0 flex items-center gap-3 text-xs text-zinc-400">
                  <span>
                    <span className="text-white font-medium">{b.total}</span> claims
                  </span>
                  <span className="text-[#3ecf8e]">
                    {b.completed} done
                  </span>
                  {b.failed > 0 && (
                    <span className="text-red-400">{b.failed} failed</span>
                  )}
                </div>

                {/* Status pill */}
                <div className="shrink-0">
                  <BatchStatusPill status={b.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function BatchStatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending:         "bg-white/10 text-zinc-400 border border-white/10",
    running:         "bg-blue-500/15 text-blue-400 border border-blue-500/30",
    completed:       "bg-[#3ecf8e]/15 text-[#3ecf8e] border border-[#3ecf8e]/30",
    partially_failed:"bg-orange-500/15 text-orange-400 border border-orange-500/30",
    failed:          "bg-red-500/15 text-red-400 border border-red-500/30",
  };
  const spinning = status === "pending" || status === "running";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
        styles[status] ?? styles.pending
      }`}
    >
      {spinning && <Loader2 size={11} className="animate-spin" />}
      {status}
    </span>
  );
}
