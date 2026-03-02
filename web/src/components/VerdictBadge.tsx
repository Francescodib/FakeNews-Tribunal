import { clsx } from "clsx";

type Label = "TRUE" | "FALSE" | "MISLEADING" | "PARTIALLY_TRUE" | "UNVERIFIABLE";

const CONFIG: Record<Label, { label: string; emoji: string; classes: string }> = {
  TRUE:           { label: "TRUE",           emoji: "✅", classes: "bg-[#3ecf8e]/15 text-[#3ecf8e] border border-[#3ecf8e]/30" },
  FALSE:          { label: "FALSE",          emoji: "❌", classes: "bg-red-500/15 text-red-400 border border-red-500/30" },
  MISLEADING:     { label: "MISLEADING",     emoji: "⚠️", classes: "bg-amber-500/15 text-amber-400 border border-amber-500/30" },
  PARTIALLY_TRUE: { label: "PARTIALLY TRUE", emoji: "🔶", classes: "bg-orange-500/15 text-orange-400 border border-orange-500/30" },
  UNVERIFIABLE:   { label: "UNVERIFIABLE",   emoji: "❓", classes: "bg-white/10 text-zinc-400 border border-white/15" },
};

export default function VerdictBadge({
  label,
  confidence,
  size = "md",
}: {
  label: Label;
  confidence?: number;
  size?: "sm" | "md" | "lg";
}) {
  const cfg = CONFIG[label] ?? CONFIG.UNVERIFIABLE;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        cfg.classes,
        size === "sm" && "px-2 py-0.5 text-xs",
        size === "md" && "px-3 py-1 text-sm",
        size === "lg" && "px-4 py-2 text-base"
      )}
    >
      <span>{cfg.emoji}</span>
      <span>{cfg.label}</span>
      {confidence !== undefined && (
        <span className="opacity-60">· {Math.round(confidence * 100)}%</span>
      )}
    </span>
  );
}
