"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { DetailPanel } from "../../components/DetailPanel";
import { MapView } from "../../components/MapView";
import { RankedList } from "../../components/RankedList";
import { WeightsPanel } from "../../components/WeightsPanel";
import { scoreAll } from "../../lib/scoring/score";
import { decodeConfig, encodeConfig, useAppStore } from "../../lib/store";
import { useBundle } from "../../lib/useBundle";

export function CityApp({ city }: { city: string }) {
  const { data: bundle, error, isLoading } = useBundle(city);
  const store = useAppStore();
  const params = useSearchParams();
  const loadedRef = useRef(false);
  const [copied, setCopied] = useState(false);

  // load shared config from URL once
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

  const scored = useMemo(
    () =>
      bundle
        ? scoreAll({ bundle, weights: store.weights, pins: store.pins, filters: store.filters })
        : [],
    [bundle, store.weights, store.pins, store.filters],
  );

  const selected = scored.find((s) => s.id === store.selectedId) ?? null;

  function share() {
    const url = `${location.origin}/${city}?c=${encodeConfig(store)}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  if (error) {
    return (
      <div className="p-8 text-sm" style={{ color: "var(--ink-2)" }}>
        Couldn&apos;t load data for “{city}”. <Link href="/" className="underline">Pick a city</Link>.
      </div>
    );
  }
  if (isLoading || !bundle) {
    return <div className="p-8 text-sm animate-pulse" style={{ color: "var(--ink-muted)" }}>Loading {city}…</div>;
  }

  return (
    <div className="h-dvh flex flex-col">
      <header
        className="flex items-center gap-3 px-4 py-2 border-b shrink-0"
        style={{ borderColor: "var(--hairline)", background: "var(--surface-1)" }}
      >
        <Link href="/" className="font-bold text-sm" style={{ color: "var(--ink-1)" }}>
          citydata
        </Link>
        <span className="text-sm" style={{ color: "var(--ink-2)" }}>
          {bundle.city.name}, {bundle.city.state} · {bundle.neighborhoods.length} neighborhoods
        </span>
        <div className="ml-auto flex items-center gap-3 text-sm">
          {store.compareIds.length >= 2 && (
            <Link
              href={`/${city}/compare?ids=${store.compareIds.join(",")}&c=${encodeConfig(store)}`}
              className="underline"
              style={{ color: "var(--accent)" }}
            >
              Compare ({store.compareIds.length})
            </Link>
          )}
          <button onClick={share} className="px-2.5 py-1 rounded text-white text-xs" style={{ background: "var(--accent)" }}>
            {copied ? "Copied!" : "Share"}
          </button>
          <Link href="/data" className="text-xs underline" style={{ color: "var(--ink-muted)" }}>
            Data & methodology
          </Link>
        </div>
      </header>

      <div className="flex-1 flex min-h-0">
        <aside
          className="w-72 shrink-0 overflow-y-auto p-4 border-r hidden md:block"
          style={{ borderColor: "var(--hairline)", background: "var(--surface-1)" }}
        >
          <WeightsPanel bundle={bundle} />
        </aside>

        <main className="flex-1 min-w-0 relative">
          <MapView
            bundle={bundle}
            scored={scored}
            onSelect={store.select}
            pins={store.pins}
            selectedId={store.selectedId}
          />
        </main>

        <aside
          className="w-80 shrink-0 border-l flex flex-col min-h-0"
          style={{ borderColor: "var(--hairline)", background: "var(--surface-1)" }}
        >
          {selected ? (
            <DetailPanel bundle={bundle} scored={selected} onClose={() => store.select(null)} />
          ) : (
            <RankedList
              scored={scored}
              onSelect={store.select}
              selectedId={store.selectedId}
              compareIds={store.compareIds}
              onToggleCompare={store.toggleCompare}
            />
          )}
        </aside>
      </div>
    </div>
  );
}
