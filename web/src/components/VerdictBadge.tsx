import { clsx } from "clsx";

type Label = "TRUE" | "FALSE" | "MISLEADING" | "PARTIALLY_TRUE" | "UNVERIFIABLE";

const CONFIG: Record<Label, { label: string; emoji: string; classes: string }> = {
  TRUE:           { label: "TRUE",           emoji: "✅", classes: "bg-green-100 text-green-800" },
  FALSE:          { label: "FALSE",          emoji: "❌", classes: "bg-red-100 text-red-800" },
  MISLEADING:     { label: "MISLEADING",     emoji: "⚠️", classes: "bg-amber-100 text-amber-800" },
  PARTIALLY_TRUE: { label: "PARTIALLY TRUE", emoji: "🔶", classes: "bg-orange-100 text-orange-800" },
  UNVERIFIABLE:   { label: "UNVERIFIABLE",   emoji: "❓", classes: "bg-slate-100 text-slate-700" },
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
