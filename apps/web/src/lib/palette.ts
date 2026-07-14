/** Sequential blue ramp (reference palette) for the 0-100 score choropleth. */
export const SCORE_RAMP = [
  "#cde2fb", // 100
  "#9ec5f4", // 200
  "#6da7ec", // 300
  "#3987e5", // 400
  "#256abf", // 500
  "#184f95", // 600
  "#0d366b", // 700
] as const;

/** Stepped class for a 0-100 score (7 equal intervals). */
export function scoreColor(score: number | null): string {
  if (score == null) return "transparent";
  const i = Math.min(SCORE_RAMP.length - 1, Math.floor((score / 100) * SCORE_RAMP.length));
  return SCORE_RAMP[i];
}

export const CONFIDENCE_BADGE = {
  high: { color: "var(--status-good)", icon: "●", label: "solid data" },
  medium: { color: "var(--status-warning)", icon: "◐", label: "partial data" },
  low: { color: "var(--status-serious)", icon: "○", label: "sparse data" },
} as const;
