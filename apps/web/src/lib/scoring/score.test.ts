import { describe, expect, it } from "vitest";
import { haversineKm, scoreAll } from "./score";
import { Bundle, MetricValue, Neighborhood } from "./types";

const mv = (value: number | null, pct: number | null, coverage = 1): MetricValue => ({
  value,
  pct,
  coverage,
  confidence: "high",
});

const hood = (id: number, slug: string, metrics: Record<string, MetricValue>): Neighborhood => ({
  id,
  slug,
  name: slug,
  centroid: [-87.6 - id * 0.01, 41.8],
  population: 10000,
  boundarySource: "city_official",
  metrics,
});

const bundle: Bundle = {
  city: { id: 1, slug: "testville", name: "Testville", state: "IL" },
  versionSet: {},
  metricsMeta: {
    violent_crime_rate: { label: "Violent crime", units: "/1k", criterion: "safety", higherIsBetter: false, intraWeight: 3, source: "t", attribution: null },
    property_crime_rate: { label: "Property crime", units: "/1k", criterion: "safety", higherIsBetter: false, intraWeight: 1, source: "t", attribution: null },
    zori: { label: "Rent", units: "USD", criterion: "affordability", higherIsBetter: false, intraWeight: 1, source: "t", attribution: null },
  },
  cityMedians: { violent_crime_rate: 5, property_crime_rate: 20, zori: 1500 },
  neighborhoods: [
    hood(1, "a", {
      violent_crime_rate: mv(2, 100),
      property_crime_rate: mv(10, 100),
      zori: mv(2000, 0),
    }),
    hood(2, "b", {
      violent_crime_rate: mv(8, 0),
      property_crime_rate: mv(30, 0),
      zori: mv(1000, 100),
    }),
    hood(3, "c", {
      violent_crime_rate: mv(5, 50),
      // property crime missing -> renormalize within safety
      zori: mv(1500, 50),
    }),
  ],
  geojson: { type: "FeatureCollection", features: [] },
};

describe("scoreAll", () => {
  it("computes weighted sums with exact contribution decomposition", () => {
    const out = scoreAll({ bundle, weights: { safety: 4, affordability: 2 }, pins: [], filters: [] });
    const a = out.find((s) => s.slug === "a")!;
    // safety = (100*3 + 100*1)/4 = 100; affordability = 0
    // fit = (100*4 + 0*2)/6 = 66.667
    expect(a.score).toBeCloseTo(66.667, 2);
    const total = a.explain.reduce((acc, e) => acc + (e.contribution ?? 0), 0);
    expect(total).toBeCloseTo(a.score!, 6);
  });

  it("renormalizes on missing metrics instead of zero-filling", () => {
    const out = scoreAll({ bundle, weights: { safety: 1 }, pins: [], filters: [] });
    const c = out.find((s) => s.slug === "c")!;
    // only violent (pct 50) present -> safety = 50, not (50*3+0)/4
    expect(c.score).toBeCloseTo(50, 5);
    const safety = c.explain.find((e) => e.criterion === "safety")!;
    expect(safety.coverage).toBeCloseTo(0.75, 5); // 3 of 4 intra-weight covered
  });

  it("ranks best-first and flags low-confidence rows as unranked", () => {
    const sparse: Bundle = {
      ...bundle,
      neighborhoods: [
        ...bundle.neighborhoods,
        hood(4, "d", { zori: mv(900, 100) }), // no safety data at all
      ],
    };
    const out = scoreAll({ bundle: sparse, weights: { safety: 4, affordability: 1 }, pins: [], filters: [] });
    const d = out.find((s) => s.slug === "d")!;
    expect(d.confidence).toBeCloseTo(0.2, 5); // only affordability (w=1) of 5 covered
    expect(d.insufficientData).toBe(true);
    expect(d.rank).toBeNull();
    const a = out.find((s) => s.slug === "a")!;
    expect(a.rank).toBe(1);
  });

  it("applies hard filters as exclusions with reasons, keeping the row", () => {
    const out = scoreAll({
      bundle,
      weights: { safety: 1, affordability: 1 },
      pins: [],
      filters: [{ metric: "zori", op: "lte", value: 1200 }],
    });
    const a = out.find((s) => s.slug === "a")!; // rent 2000 > 1200
    expect(a.excluded).toBe(true);
    expect(a.rank).toBeNull();
    expect(a.exclusionReasons[0]).toMatch(/Rent/);
    const b = out.find((s) => s.slug === "b")!; // rent 1000 ok
    expect(b.excluded).toBe(false);
    expect(b.rank).toBe(1);
  });

  it("scores pin proximity: nearer neighborhoods rank higher", () => {
    const out = scoreAll({
      bundle,
      weights: { places: 5 },
      pins: [{ id: "p1", label: "Office", lon: -87.61, lat: 41.8, weight: 5 }],
      filters: [],
    });
    // hood 1 centroid -87.61 (distance 0), hood 3 farthest at -87.63
    expect(out[0].slug).toBe("a");
    expect(out[0].score).toBeCloseTo(100, 5);
    expect(out[2].slug).toBe("c");
    const pinMetric = out[0].explain[0].metrics[0];
    expect(pinMetric.label).toBe("Distance to Office");
    expect(pinMetric.raw).toBeCloseTo(0, 1);
  });

  it("re-ranks a 77-neighborhood bundle well under the interactivity budget", () => {
    const big: Bundle = {
      ...bundle,
      neighborhoods: Array.from({ length: 77 }, (_, i) =>
        hood(i + 1, `h${i}`, {
          violent_crime_rate: mv(i, ((77 - i) / 77) * 100),
          property_crime_rate: mv(i * 2, ((77 - i) / 77) * 100),
          zori: mv(1000 + i * 10, (i / 77) * 100),
        }),
      ),
    };
    const t0 = performance.now();
    for (let i = 0; i < 100; i++) {
      scoreAll({
        bundle: big,
        weights: { safety: 3, affordability: 2, places: 2 },
        pins: [{ id: "p", label: "Work", lon: -87.7, lat: 41.85, weight: 3 }],
        filters: [{ metric: "zori", op: "lte", value: 1700 }],
      });
    }
    const perRun = (performance.now() - t0) / 100;
    expect(perRun).toBeLessThan(16); // one frame
  });
});

describe("haversineKm", () => {
  it("Chicago Loop to O'Hare is ~25km", () => {
    expect(haversineKm([-87.627, 41.879], [-87.905, 41.973])).toBeGreaterThan(20);
    expect(haversineKm([-87.627, 41.879], [-87.905, 41.973])).toBeLessThan(30);
  });
});
