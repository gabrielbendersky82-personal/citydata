import { CONFIDENCE_BADGE } from "../lib/palette";

/** Icon + label pairing — confidence is never color alone. */
export function ConfidenceBadge({ level }: { level: "high" | "medium" | "low" }) {
  const b = CONFIDENCE_BADGE[level];
  return (
    <span
      className="inline-flex items-center gap-1 text-xs whitespace-nowrap"
      style={{ color: "var(--ink-2)" }}
      title={`Data coverage: ${level}`}
    >
      <span aria-hidden style={{ color: b.color }}>{b.icon}</span>
      {b.label}
    </span>
  );
}

export function confidenceLevel(c: number): "high" | "medium" | "low" {
  return c >= 0.9 ? "high" : c >= 0.6 ? "medium" : "low";
}
