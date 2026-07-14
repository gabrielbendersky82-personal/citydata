"use client";
import { CRITERIA, PERSONAS } from "../lib/scoring/criteria";
import { Bundle, SliderKey } from "../lib/scoring/types";
import { useAppStore } from "../lib/store";
import { PinsEditor } from "./PinsEditor";
import { FiltersEditor } from "./FiltersEditor";

export function WeightsPanel({ bundle }: { bundle: Bundle }) {
  const { weights, persona, setWeight, applyPersona } = useAppStore();

  // criteria with any data in this city (places is always shown)
  const withData = new Set(
    Object.entries(bundle.metricsMeta)
      .filter(([key]) => bundle.cityMedians[key] != null)
      .map(([, meta]) => meta.criterion),
  );

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-sm font-semibold mb-2" style={{ color: "var(--ink-1)" }}>
          Start from a preset
        </h2>
        <div className="flex flex-wrap gap-1.5">
          {PERSONAS.map((p) => (
            <button
              key={p.key}
              onClick={() => applyPersona(p.key, p.weights)}
              className="px-2.5 py-1 rounded-full text-xs border transition-colors"
              style={{
                borderColor: persona === p.key ? "var(--accent)" : "var(--border)",
                background: persona === p.key ? "color-mix(in srgb, var(--accent) 12%, transparent)" : "transparent",
                color: "var(--ink-1)",
              }}
            >
              {p.emoji} {p.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold mb-1" style={{ color: "var(--ink-1)" }}>
          What matters to you?
        </h2>
        <p className="text-xs mb-3" style={{ color: "var(--ink-muted)" }}>
          0 = ignore · 5 = top priority. Rankings update instantly.
        </p>
        <div className="space-y-3">
          {CRITERIA.map((c) => {
            const available = c.key === "places" || withData.has(c.key as never);
            const value = weights[c.key as SliderKey] ?? 0;
            return (
              <div key={c.key} className={available ? "" : "opacity-45"}>
                <div className="flex items-baseline justify-between">
                  <label htmlFor={`w-${c.key}`} className="text-sm" style={{ color: "var(--ink-1)" }}>
                    {c.label}
                  </label>
                  <span className="text-xs tnum" style={{ color: "var(--ink-2)" }}>{value}</span>
                </div>
                <input
                  id={`w-${c.key}`}
                  type="range"
                  min={0}
                  max={5}
                  step={1}
                  value={value}
                  disabled={!available}
                  onChange={(e) => setWeight(c.key as SliderKey, Number(e.target.value))}
                  className="w-full"
                />
                <p className="text-[11px] leading-tight" style={{ color: "var(--ink-muted)" }}>
                  {available ? c.blurb : `${c.blurb} — no data yet for this city`}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      <PinsEditor />
      <FiltersEditor bundle={bundle} />
    </div>
  );
}
