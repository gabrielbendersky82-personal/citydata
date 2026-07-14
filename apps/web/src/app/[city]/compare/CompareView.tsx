"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef } from "react";
import { ConfidenceBadge, confidenceLevel } from "../../../components/ConfidenceBadge";
import { CRITERIA } from "../../../lib/scoring/criteria";
import { scoreAll } from "../../../lib/scoring/score";
import { scoreColor } from "../../../lib/palette";
import { decodeConfig, useAppStore } from "../../../lib/store";
import { useBundle } from "../../../lib/useBundle";

export function CompareView({ city }: { city: string }) {
  const { data: bundle } = useBundle(city);
  const params = useSearchParams();
  const store = useAppStore();
  const loadedRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    const raw = params.get("c");
    if (raw) {
      const cfg = decodeConfig(raw);
      if (cfg) store.loadConfig(cfg);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ids = (params.get("ids") ?? "")
    .split(",")
    .map(Number)
    .filter((n) => Number.isFinite(n))
    .slice(0, 4);

  const scored = useMemo(
    () =>
      bundle
        ? scoreAll({ bundle, weights: store.weights, pins: store.pins, filters: store.filters })
        : [],
    [bundle, store.weights, store.pins, store.filters],
  );

  if (!bundle) return <div className="p-8 text-sm animate-pulse" style={{ color: "var(--ink-muted)" }}>Loading…</div>;

  const columns = ids
    .map((id) => scored.find((s) => s.id === id))
    .filter((s): s is NonNullable<typeof s> => Boolean(s));

  if (columns.length < 2) {
    return (
      <div className="p-8 text-sm" style={{ color: "var(--ink-2)" }}>
        Pick at least two neighborhoods to compare. <Link className="underline" href={`/${city}`}>Back to the map</Link>
      </div>
    );
  }

  const activeCriteria = CRITERIA.filter((c) => (store.weights[c.key] ?? 0) > 0);

  return (
    <main className="p-6 max-w-5xl mx-auto">
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-xl font-bold" style={{ color: "var(--ink-1)" }}>
          Side by side — {bundle.city.name}
        </h1>
        <Link href={`/${city}`} className="text-sm underline" style={{ color: "var(--accent)" }}>
          ← Back to the map
        </Link>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr>
              <th className="text-left p-2 font-normal" style={{ color: "var(--ink-muted)" }}>
                Your weights →
              </th>
              {columns.map((s) => (
                <th key={s.id} className="p-2 text-left" style={{ color: "var(--ink-1)" }}>
                  <div className="font-semibold">{s.name}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-lg font-bold tnum rounded px-1.5 text-white" style={{ background: scoreColor(s.score) }}>
                      {s.score != null ? Math.round(s.score) : "—"}
                    </span>
                    <span className="text-xs font-normal" style={{ color: "var(--ink-muted)" }}>
                      {s.rank != null ? `#${s.rank}` : s.excluded ? "excluded" : "unranked"}
                    </span>
                  </div>
                  <div className="mt-1"><ConfidenceBadge level={confidenceLevel(s.confidence)} /></div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {activeCriteria.map((c) => (
              <tr key={c.key} className="border-t" style={{ borderColor: "var(--hairline)" }}>
                <td className="p-2" style={{ color: "var(--ink-2)" }}>
                  {c.label}
                  <span className="text-xs tnum" style={{ color: "var(--ink-muted)" }}> ·w{store.weights[c.key]}</span>
                </td>
                {columns.map((s) => {
                  const e = s.explain.find((x) => x.criterion === c.key);
                  return (
                    <td key={s.id} className="p-2">
                      {e?.score != null ? (
                        <div className="flex items-center gap-2">
                          <span className="tnum font-medium" style={{ color: "var(--ink-1)" }}>{Math.round(e.score)}</span>
                          <div className="flex-1 max-w-28 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--hairline)" }}>
                            <div className="h-full rounded-full" style={{ width: `${e.score}%`, background: scoreColor(e.score) }} />
                          </div>
                        </div>
                      ) : (
                        <span style={{ color: "var(--ink-muted)" }}>no data</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-[11px]" style={{ color: "var(--ink-muted)" }}>
        Criterion scores are within-city percentiles (100 = best in {bundle.city.name}) weighted by your sliders.
        Decision support, not advice.
      </p>
    </main>
  );
}
