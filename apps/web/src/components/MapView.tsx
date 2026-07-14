"use client";
import maplibregl, { Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import { Bundle, Pin, ScoredNeighborhood } from "../lib/scoring/types";
import { SCORE_RAMP } from "../lib/palette";

const BASEMAP = "https://tiles.openfreemap.org/styles/positron";

/** Fallback style if the basemap host is unreachable — our polygons still render. */
const BLANK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "transparent" } }],
};

const scoreColorExpr = (): maplibregl.ExpressionSpecification => [
  "step",
  ["coalesce", ["feature-state", "score"], -1],
  "rgba(137,135,129,0.25)", // no score -> muted hatch-ish gray
  0, SCORE_RAMP[0],
  100 / 7, SCORE_RAMP[1],
  (100 / 7) * 2, SCORE_RAMP[2],
  (100 / 7) * 3, SCORE_RAMP[3],
  (100 / 7) * 4, SCORE_RAMP[4],
  (100 / 7) * 5, SCORE_RAMP[5],
  (100 / 7) * 6, SCORE_RAMP[6],
];

export function MapView({
  bundle,
  scored,
  onSelect,
  pins,
  selectedId,
}: {
  bundle: Bundle;
  scored: ScoredNeighborhood[];
  onSelect: (id: number) => void;
  pins: Pin[];
  selectedId: number | null;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const readyRef = useRef(false);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: BASEMAP,
      // OpenFreeMap serves OSM tiles: attribution is mandatory
      attributionControl: {
        compact: true,
        customAttribution: "© OpenStreetMap contributors · basemap by OpenFreeMap",
      },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    map.on("error", (e) => {
      // basemap unreachable (offline dev) -> fall back to blank canvas once
      if (!readyRef.current && String(e.error?.message ?? "").match(/Failed to fetch|NetworkError|load/i)) {
        map.setStyle(BLANK_STYLE);
      }
    });

    const addData = () => {
      if (map.getSource("hoods")) return;
      map.addSource("hoods", { type: "geojson", data: bundle.geojson, promoteId: undefined });
      map.addLayer({
        id: "hood-fill",
        type: "fill",
        source: "hoods",
        paint: { "fill-color": scoreColorExpr(), "fill-opacity": 0.72 },
      });
      map.addLayer({
        id: "hood-line",
        type: "line",
        source: "hoods",
        paint: { "line-color": "rgba(11,11,11,0.35)", "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 2.5, 0.6] },
      });
      const bounds = new maplibregl.LngLatBounds();
      for (const n of bundle.neighborhoods) bounds.extend(n.centroid);
      map.fitBounds(bounds, { padding: 24, animate: false });

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });
      map.on("mousemove", "hood-fill", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const st = map.getFeatureState({ source: "hoods", id: f.id! });
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<strong>${f.properties!.name}</strong><br/>` +
              (st.score != null ? `fit score ${Math.round(st.score)}` : "no score"),
          )
          .addTo(map);
      });
      map.on("mouseleave", "hood-fill", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
      map.on("click", "hood-fill", (e) => {
        const f = e.features?.[0];
        if (f?.id != null) onSelect(Number(f.id));
      });
      readyRef.current = true;
      applyScores();
    };

    const applyScores = () => {
      for (const s of scoredRef.current) {
        map.setFeatureState(
          { source: "hoods", id: s.id },
          { score: s.excluded || s.insufficientData ? null : s.score, selected: s.id === selectedRef.current },
        );
      }
    };

    map.on("load", addData);
    map.on("styledata", () => {
      // re-add our layers after a style fallback swap
      if (map.isStyleLoaded() && !map.getSource("hoods")) addData();
    });

    return () => {
      map.remove();
      mapRef.current = null;
      readyRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundle]);

  // keep latest scores/selection in refs so map callbacks see fresh data
  const scoredRef = useRef(scored);
  scoredRef.current = scored;
  const selectedRef = useRef(selectedId);
  selectedRef.current = selectedId;

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current || !map.getSource("hoods")) return;
    for (const s of scored) {
      map.setFeatureState(
        { source: "hoods", id: s.id },
        { score: s.excluded || s.insufficientData ? null : s.score, selected: s.id === selectedId },
      );
    }
  }, [scored, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = pins.map((p) =>
      new maplibregl.Marker({ color: "#d03b3b" })
        .setLngLat([p.lon, p.lat])
        .setPopup(new maplibregl.Popup({ offset: 12 }).setText(p.label))
        .addTo(map),
    );
  }, [pins]);

  return (
    <div className="relative h-full w-full">
      <div ref={container} className="h-full w-full" />
      <MapLegend />
    </div>
  );
}

function MapLegend() {
  return (
    <div
      className="absolute bottom-6 left-2 rounded px-2.5 py-1.5 text-[11px] shadow-sm border"
      style={{ background: "var(--surface-1)", borderColor: "var(--border)", color: "var(--ink-2)" }}
    >
      <div className="mb-1">Fit score</div>
      <div className="flex items-center gap-0">
        {SCORE_RAMP.map((c) => (
          <span key={c} className="inline-block h-2.5 w-5 first:rounded-l last:rounded-r" style={{ background: c }} />
        ))}
      </div>
      <div className="flex justify-between tnum" style={{ color: "var(--ink-muted)" }}>
        <span>0</span>
        <span>100</span>
      </div>
    </div>
  );
}
