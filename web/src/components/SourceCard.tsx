import { clsx } from "clsx";
import { ExternalLink } from "lucide-react";
import type { Source } from "@/lib/api";

const TIER_STYLE: Record<string, string> = {
  high:    "bg-[#3ecf8e]/15 text-[#3ecf8e] border border-[#3ecf8e]/30",
  medium:  "bg-blue-500/15 text-blue-400 border border-blue-500/30",
  low:     "bg-red-500/15 text-red-400 border border-red-500/30",
  unknown: "bg-white/10 text-zinc-500 border border-white/10",
};

export default function SourceCard({ source }: { source: Source }) {
  const tier = source.credibility_tier ?? "unknown";
  return (
    <div className="rounded-xl bg-[#1a1a1a] border border-white/10 p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-white hover:text-[#3ecf8e] line-clamp-1 flex items-center gap-1 transition-colors"
          >
            {source.title || source.domain}
            <ExternalLink size={12} className="shrink-0 opacity-40" />
          </a>
          <p className="text-zinc-500 text-xs mt-0.5">{source.domain}</p>
        </div>
        <span className={clsx("shrink-0 rounded-full px-2 py-0.5 text-xs font-medium", TIER_STYLE[tier])}>
          {tier}
        </span>
      </div>
      {source.snippet && (
        <p className="mt-2 text-zinc-500 line-clamp-2 text-xs leading-relaxed">
          {source.snippet}
        </p>
      )}
      {source.credibility_note && (
        <p className="mt-1 text-xs italic text-zinc-600">{source.credibility_note}</p>
      )}
    </div>
  );
}
