"use client";
import { useState } from "react";
import { CRITERIA } from "../lib/scoring/criteria";
import { Bundle, CriterionExplain, ScoredNeighborhood } from "../lib/scoring/types";
import { ConfidenceBadge, confidenceLevel } from "./ConfidenceBadge";
import { scoreColor } from "../lib/palette";

const fmt = (v: number | null, units: string | null): string => {
  if (v == null) return "—";
  const n =
    Math.abs(v) >= 1000
      ? Math.round(v).toLocaleString("en-US")
      : Math.abs(v) >= 100
        ? v.toFixed(0)
        : v.toFixed(1);
  if (!units) return n;
  if (units === "USD") return `$${n}`;
  if (units === "USD/mo") return `$${n}/mo`;
  if (units === "%") return `${n}%`;
  return `${n} ${units}`;
};

const criterionLabel = (key: string) => CRITERIA.find((c) => c.key === key)?.label ?? key;

/** The "why": exact contribution decomposition + per-metric evidence. */
export function DetailPanel({
  bundle,
  scored,
  onClose,
}: {
  bundle: Bundle;
  scored: ScoredNeighborhood;
  onClose?: () => void;
}) {
  const hood = bundle.neighborhoods.find((n) => n.id === scored.id);
  const active = scored.explain.filter((e) => e.weight > 0);
  const maxContribution = Math.max(1, ...active.map((e) => e.contribution ?? 0));

  return (
    <div className="h-full overflow-y-auto p-4" style={{ background: "var(--surface-1)" }}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold" style={{ color: "var(--ink-1)" }}>{scored.name}</h2>
          <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
            {hood?.population != null && `${hood.population.toLocaleString("en-US")} residents · `}
            {scored.rank != null ? `#${scored.rank} for your priorities` : scored.excluded ? "excluded by your limits" : "not ranked (sparse data)"}
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {scored.score != null && (
            <span
              className="text-xl font-bold tnum rounded px-2 py-0.5 text-white"
              style={{ background: scoreColor(scored.score) }}
            >
              {Math.round(scored.score)}
            </span>
          )}
          {onClose && (
            <button onClick={onClose} aria-label="Close details" style={{ color: "var(--ink-muted)" }}>✕</button>
          )}
        </div>
      </div>

      <div className="mt-1 mb-3">
        <ConfidenceBadge level={confidenceLevel(scored.confidence)} />
      </div>

      {scored.exclusionReasons.length > 0 && (
        <p className="mb-3 text-xs rounded border px-2 py-1.5" style={{ borderColor: "var(--status-critical)", color: "var(--ink-2)" }}>
          Excluded: {scored.exclusionReasons.join("; ")}
        </p>
      )}

      <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--ink-1)" }}>
        How the score adds up
      </h3>
      <p className="text-xs mb-2" style={{ color: "var(--ink-muted)" }}>
        Each bar is that criterion&apos;s exact contribution — they sum to the total.
      </p>
      <div className="space-y-2">
        {active.map((e) => (
          <CriterionRow key={e.criterion} explain={e} max={maxContribution} />
        ))}
      </div>

      <VersionFootnote bundle={bundle} />
    </div>
  );
}

function CriterionRow({ explain: e, max }: { explain: CriterionExplain; max: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border rounded" style={{ borderColor: "var(--hairline)" }}>
      <button className="w-full px-2.5 py-2 text-left" onClick={() => setOpen(!open)}>
        <div className="flex items-baseline justify-between gap-2 text-sm">
          <span style={{ color: "var(--ink-1)" }}>{criterionLabel(e.criterion)}</span>
          <span className="tnum text-xs" style={{ color: "var(--ink-2)" }}>
            {e.score != null ? `${Math.round(e.score)}/100 · weight ${e.weight}` : "no data"}
            {e.contribution != null && ` · +${e.contribution.toFixed(1)} pts`}
          </span>
        </div>
        <div className="mt-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--hairline)" }}>
          {e.contribution != null && (
            <div
              className="h-full rounded-full"
              style={{ width: `${(e.contribution / max) * 100}%`, background: "var(--accent)" }}
            />
          )}
        </div>
        {e.coverage < 1 && (
          <p className="mt-0.5 text-[11px]" style={{ color: "var(--ink-muted)" }}>
            {Math.round(e.coverage * 100)}% of this criterion&apos;s data available — weights renormalized
          </p>
        )}
      </button>
      {open && (
        <div className="px-2.5 pb-2 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left" style={{ color: "var(--ink-muted)" }}>
                <th className="py-1 pr-2 font-normal">Metric</th>
                <th className="py-1 pr-2 font-normal text-right">Here</th>
                <th className="py-1 pr-2 font-normal text-right">City median</th>
                <th className="py-1 font-normal text-right">Percentile</th>
              </tr>
            </thead>
            <tbody>
              {e.metrics.map((m) => (
                <tr key={m.key} className="border-t" style={{ borderColor: "var(--hairline)", color: "var(--ink-2)" }}>
                  <td className="py-1 pr-2">
                    {m.label}
                    {m.confidence === "low" && <span title="sparse/high-uncertainty data" style={{ color: "var(--status-serious)" }}> ○</span>}
                  </td>
                  <td className="py-1 pr-2 text-right tnum" style={{ color: "var(--ink-1)" }}>{fmt(m.raw, m.units)}</td>
                  <td className="py-1 pr-2 text-right tnum">{fmt(m.cityMedian, m.units)}</td>
                  <td className="py-1 text-right tnum">{m.pct != null ? Math.round(m.pct) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {[...new Set(e.metrics.map((m) => m.attribution).filter(Boolean))].length > 0 && (
            <p className="mt-1 text-[10px]" style={{ color: "var(--ink-muted)" }}>
              Data: {[...new Set(e.metrics.map((m) => m.attribution).filter(Boolean))].join(" · ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function VersionFootnote({ bundle }: { bundle: Bundle }) {
  const entries = Object.entries(bundle.versionSet);
  return (
    <div className="mt-4 pt-3 border-t text-[11px] leading-relaxed" style={{ borderColor: "var(--hairline)", color: "var(--ink-muted)" }}>
      <p>
        Decision support, not advice — verify independently before signing anything. Percentiles compare
        neighborhoods <em>within this city only</em>.
      </p>
      {entries.length > 0 && (
        <p className="mt-1">
          Data vintages: {entries.map(([src, v]) => `${src} (${v.vintage})`).join(", ")}.
        </p>
      )}
    </div>
  );
}
