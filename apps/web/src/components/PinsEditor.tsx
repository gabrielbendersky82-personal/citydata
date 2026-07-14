"use client";
import { useState } from "react";
import { useAppStore } from "../lib/store";

/** Add "my places" by address (geocoded via our proxy) and weight proximity. */
export function PinsEditor() {
  const { pins, addPin, removePin, setPinWeight } = useAppStore();
  const [label, setLabel] = useState("");
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!address.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/geocode", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ address }),
      });
      const data = await r.json();
      if (!r.ok || data.lon == null) {
        setError(data.error ?? "Address not found — try adding city and state.");
        return;
      }
      addPin({
        id: crypto.randomUUID().slice(0, 8),
        label: label.trim() || address.split(",")[0],
        lon: data.lon,
        lat: data.lat,
        weight: 3,
      });
      setLabel("");
      setAddress("");
    } catch {
      setError("Geocoding failed — try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="text-sm font-semibold mb-1" style={{ color: "var(--ink-1)" }}>My places</h2>
      <p className="text-xs mb-2" style={{ color: "var(--ink-muted)" }}>
        Pin an office, family, gym — closer neighborhoods score higher (straight-line distance).
      </p>
      <form onSubmit={submit} className="space-y-1.5">
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Label (e.g. Office)"
          className="w-full rounded border px-2 py-1 text-sm bg-transparent"
          style={{ borderColor: "var(--border)", color: "var(--ink-1)" }}
        />
        <div className="flex gap-1.5">
          <input
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Address"
            className="flex-1 rounded border px-2 py-1 text-sm bg-transparent"
            style={{ borderColor: "var(--border)", color: "var(--ink-1)" }}
          />
          <button
            type="submit"
            disabled={busy || !address.trim()}
            className="px-3 py-1 rounded text-sm text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            {busy ? "…" : "Pin"}
          </button>
        </div>
      </form>
      {error && <p className="text-xs mt-1" style={{ color: "var(--status-critical)" }}>{error}</p>}
      <ul className="mt-2 space-y-2">
        {pins.map((p) => (
          <li key={p.id} className="text-sm">
            <div className="flex items-center justify-between">
              <span style={{ color: "var(--ink-1)" }}>📍 {p.label}</span>
              <span className="flex items-center gap-2">
                <span className="text-xs tnum" style={{ color: "var(--ink-2)" }}>{p.weight}</span>
                <button
                  onClick={() => removePin(p.id)}
                  aria-label={`Remove ${p.label}`}
                  className="text-xs"
                  style={{ color: "var(--ink-muted)" }}
                >
                  ✕
                </button>
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={5}
              step={1}
              value={p.weight}
              onChange={(e) => setPinWeight(p.id, Number(e.target.value))}
              className="w-full"
              aria-label={`Weight for ${p.label}`}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
