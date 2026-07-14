export type Criterion =
  | "safety"
  | "affordability"
  | "socioeconomics"
  | "schools"
  | "walkability"
  | "transit"
  | "environment"
  | "hazard";

export const PLACES_CRITERION = "places" as const;
export type SliderKey = Criterion | typeof PLACES_CRITERION;

export type Confidence = "high" | "medium" | "low";

export interface MetricMeta {
  label: string;
  units: string | null;
  criterion: Criterion;
  higherIsBetter: boolean;
  intraWeight: number;
  source: string;
  attribution: string | null;
}

export interface MetricValue {
  value: number | null;
  pct: number | null; // 0-100 within city, direction-adjusted (100 = best)
  coverage: number | null; // 0-1
  confidence: Confidence | null;
}

export interface Neighborhood {
  id: number;
  slug: string;
  name: string;
  centroid: [number, number]; // lon, lat
  population: number | null;
  boundarySource: string;
  metrics: Record<string, MetricValue>;
}

export interface Bundle {
  city: { id: number; slug: string; name: string; state: string };
  versionSet: Record<string, { vintage: string; retrievedAt: string }>;
  metricsMeta: Record<string, MetricMeta>;
  cityMedians: Record<string, number | null>;
  neighborhoods: Neighborhood[];
  geojson: import("geojson").FeatureCollection;
}

/** User weights per criterion slider, 0-5. */
export type Weights = Partial<Record<SliderKey, number>>;

export interface Pin {
  id: string;
  label: string;
  lon: number;
  lat: number;
  weight: number; // 0-5, within the "My Places" criterion
}

export interface Filter {
  metric: string;
  op: "lte" | "gte";
  value: number;
}

export interface MetricExplain {
  key: string;
  label: string;
  units: string | null;
  raw: number | null;
  pct: number | null;
  intraWeight: number;
  cityMedian: number | null;
  confidence: Confidence | null;
  higherIsBetter: boolean;
  source: string;
  attribution: string | null;
}

export interface CriterionExplain {
  criterion: SliderKey;
  weight: number;
  score: number | null; // 0-100
  coverage: number; // 0-1 within this criterion
  contribution: number | null; // points contributed to the total (sums to total)
  metrics: MetricExplain[];
}

export interface ScoredNeighborhood {
  id: number;
  slug: string;
  name: string;
  score: number | null; // 0-100 weighted fit
  confidence: number; // 0-1 weight-covered share
  rank: number | null;
  excluded: boolean;
  exclusionReasons: string[];
  insufficientData: boolean;
  explain: CriterionExplain[];
}
