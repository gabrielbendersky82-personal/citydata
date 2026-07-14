"use client";
import { compressToEncodedURIComponent, decompressFromEncodedURIComponent } from "lz-string";
import { create } from "zustand";
import { DEFAULT_WEIGHTS } from "./scoring/criteria";
import { Filter, Pin, Weights } from "./scoring/types";

interface ShareableConfig {
  w: Weights;
  f: Filter[];
  p: Pin[];
  persona?: string;
}

interface AppState {
  weights: Weights;
  filters: Filter[];
  pins: Pin[];
  persona: string | null;
  selectedId: number | null;
  compareIds: number[];
  setWeight: (k: keyof Weights, v: number) => void;
  applyPersona: (key: string, weights: Weights) => void;
  setFilters: (f: Filter[]) => void;
  addPin: (p: Pin) => void;
  removePin: (id: string) => void;
  setPinWeight: (id: string, w: number) => void;
  select: (id: number | null) => void;
  toggleCompare: (id: number) => void;
  loadConfig: (c: ShareableConfig) => void;
}

export const useAppStore = create<AppState>((set) => ({
  weights: { ...DEFAULT_WEIGHTS },
  filters: [],
  pins: [],
  persona: "balanced",
  selectedId: null,
  compareIds: [],
  setWeight: (k, v) =>
    set((s) => ({ weights: { ...s.weights, [k]: v }, persona: null })),
  applyPersona: (key, weights) => set({ persona: key, weights: { ...weights } }),
  setFilters: (filters) => set({ filters }),
  addPin: (p) => set((s) => ({ pins: [...s.pins, p] })),
  removePin: (id) => set((s) => ({ pins: s.pins.filter((p) => p.id !== id) })),
  setPinWeight: (id, w) =>
    set((s) => ({ pins: s.pins.map((p) => (p.id === id ? { ...p, weight: w } : p)) })),
  select: (selectedId) => set({ selectedId }),
  toggleCompare: (id) =>
    set((s) => ({
      compareIds: s.compareIds.includes(id)
        ? s.compareIds.filter((x) => x !== id)
        : s.compareIds.length < 4
          ? [...s.compareIds, id]
          : s.compareIds,
    })),
  loadConfig: (c) =>
    set({ weights: c.w, filters: c.f ?? [], pins: c.p ?? [], persona: c.persona ?? null }),
}));

export function encodeConfig(s: Pick<AppState, "weights" | "filters" | "pins" | "persona">): string {
  const cfg: ShareableConfig = { w: s.weights, f: s.filters, p: s.pins, persona: s.persona ?? undefined };
  return compressToEncodedURIComponent(JSON.stringify(cfg));
}

export function decodeConfig(raw: string): ShareableConfig | null {
  try {
    const json = decompressFromEncodedURIComponent(raw);
    if (!json) return null;
    const cfg = JSON.parse(json);
    if (!cfg || typeof cfg !== "object" || !cfg.w) return null;
    return cfg as ShareableConfig;
  } catch {
    return null;
  }
}
