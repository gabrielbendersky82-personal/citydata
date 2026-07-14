import { scoreColor } from "../lib/palette";

/** Thin horizontal 0-100 bar; 4px rounded data end, hairline track. */
export function ScoreBar({ value, height = 6 }: { value: number | null; height?: number }) {
  return (
    <div
      className="w-full rounded-full overflow-hidden"
      style={{ height, background: "var(--hairline)" }}
      role="img"
      aria-label={value != null ? `score ${Math.round(value)} of 100` : "no score"}
    >
      {value != null && (
        <div
          className="h-full rounded-full transition-[width] duration-150"
          style={{ width: `${Math.max(2, value)}%`, background: scoreColor(value) }}
        />
      )}
    </div>
  );
}
