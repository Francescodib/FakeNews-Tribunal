"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { DebateRound } from "@/lib/api";
import SourceCard from "./SourceCard";

export default function DebateRoundCard({ round }: { round: DebateRound }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-2xl bg-white shadow-sm overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-slate-50 transition-colors"
      >
        <span className="font-medium text-slate-800">Round {round.round_number}</span>
        <span className="text-slate-400">
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>
      </button>

      {open && (
        <div className="divide-y divide-slate-100">
          {/* Researcher */}
          <div className="px-5 py-4">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-blue-600 mb-2">
              Researcher
            </h4>
            <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
              {round.researcher_report}
            </p>
            {round.researcher_sources.length > 0 && (
              <div className="mt-3 grid gap-2">
                {round.researcher_sources.map((s, i) => (
                  <SourceCard key={i} source={s} />
                ))}
              </div>
            )}
          </div>

          {/* Devil's Advocate */}
          <div className="px-5 py-4">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-red-500 mb-2">
              Devil&apos;s Advocate
            </h4>
            <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
              {round.advocate_challenge}
            </p>
            {round.advocate_counter_sources.length > 0 && (
              <div className="mt-3 grid gap-2">
                {round.advocate_counter_sources.map((s, i) => (
                  <SourceCard key={i} source={s} />
                ))}
              </div>
            )}
          </div>

          {/* Judge continuation */}
          {round.judge_continuation_reason && (
            <div className="px-5 py-4 bg-amber-50">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-amber-700 mb-1">
                Judge → Continue
              </h4>
              <p className="text-sm text-amber-800">{round.judge_continuation_reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
