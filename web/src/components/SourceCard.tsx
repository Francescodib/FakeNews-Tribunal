import { clsx } from "clsx";
import { ExternalLink } from "lucide-react";
import type { Source } from "@/lib/api";

const TIER_STYLE: Record<string, string> = {
  high:    "bg-green-100 text-green-700",
  medium:  "bg-blue-100 text-blue-700",
  low:     "bg-red-100 text-red-700",
  unknown: "bg-slate-100 text-slate-500",
};

export default function SourceCard({ source }: { source: Source }) {
  const tier = source.credibility_tier ?? "unknown";
  return (
    <div className="rounded-xl bg-slate-50 p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-slate-900 hover:text-blue-600 line-clamp-1 flex items-center gap-1"
          >
            {source.title || source.domain}
            <ExternalLink size={12} className="shrink-0 opacity-40" />
          </a>
          <p className="text-slate-400 text-xs mt-0.5">{source.domain}</p>
        </div>
        <span className={clsx("shrink-0 rounded-full px-2 py-0.5 text-xs font-medium", TIER_STYLE[tier])}>
          {tier}
        </span>
      </div>
      {source.snippet && (
        <p className="mt-2 text-slate-500 line-clamp-2 text-xs leading-relaxed">
          {source.snippet}
        </p>
      )}
      {source.credibility_note && (
        <p className="mt-1 text-xs italic text-slate-400">{source.credibility_note}</p>
      )}
    </div>
  );
}
