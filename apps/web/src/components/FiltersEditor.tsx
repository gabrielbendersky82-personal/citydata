"use client";
import { Bundle } from "../lib/scoring/types";
import { useAppStore } from "../lib/store";

/** Hard filters: exclude, don't rank. MVP set: the metrics people cap. */
const FILTERABLE: { metric: string; label: string; op: "lte"; step: number }[] = [
  { metric: "zori", label: "Max typical rent ($/mo)", op: "lte", step: 100 },
  { metric: "zhvi", label: "Max typical home value ($)", op: "lte", step: 25000 },
  { metric: "violent_crime_rate", label: "Max violent crime (/1k/yr)", op: "lte", step: 1 },
  { metric: "flood_sfha_pct", label: "Max flood-zone share (%)", op: "lte", step: 1 },
];

export function FiltersEditor({ bundle }: { bundle: Bundle }) {
  const { filters, setFilters } = useAppStore();
  const available = FILTERABLE.filter((f) => bundle.cityMedians[f.metric] != null);
  if (!available.length) return null;

  function setFilter(metric: string, op: "lte", raw: string) {
    const rest = filters.filter((f) => f.metric !== metric);
    const value = raw === "" ? null : Number(raw);
    setFilters(value == null || Number.isNaN(value) ? rest : [...rest, { metric, op, value }]);
  }

  return (
    <div>
      <h2 className="text-sm font-semibold mb-1" style={{ color: "var(--ink-1)" }}>Hard limits</h2>
      <p className="text-xs mb-2" style={{ color: "var(--ink-muted)" }}>
        Neighborhoods over a limit are excluded, not just ranked lower.
      </p>
      <div className="space-y-2">
        {available.map((f) => {
          const current = filters.find((x) => x.metric === f.metric)?.value ?? "";
          return (
            <label key={f.metric} className="block text-xs" style={{ color: "var(--ink-2)" }}>
              {f.label}
              <input
                type="number"
                inputMode="numeric"
                step={f.step}
                value={current}
                placeholder="no limit"
                onChange={(e) => setFilter(f.metric, f.op, e.target.value)}
                className="mt-0.5 w-full rounded border px-2 py-1 text-sm bg-transparent tnum"
                style={{ borderColor: "var(--border)", color: "var(--ink-1)" }}
              />
            </label>
          );
        })}
      </div>
    </div>
  );
}
