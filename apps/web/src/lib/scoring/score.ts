/**
 * Pure scoring engine. All heavy normalization is precomputed server-side
 * (per-metric within-city percentiles); this module only does weighted
 * aggregation, so re-ranking on slider changes is a few thousand
 * multiplications — instant.
 *
 * Rules (see docs/PLAN.md §e):
 *  - criterion score = intra-weighted mean of member metric percentiles,
 *    renormalized over metrics WITH data (missing ≠ zero)
 *  - overall = user-weighted mean of criterion scores, renormalized over
 *    criteria with any coverage
 *  - hard filters exclude before ranking; excluded rows keep their score
 *  - confidence = user-weight-covered share; < MIN_CONFIDENCE → unranked
 */
import {
  Bundle,
  Criterion,
  CriterionExplain,
  Filter,
  MetricExplain,
  Neighborhood,
  PLACES_CRITERION,
  Pin,
  ScoredNeighborhood,
  SliderKey,
  Weights,
} from "./types";

export const MIN_CONFIDENCE = 0.6;

const R_EARTH_KM = 6371;

export function haversineKm(a: [number, number], b: [number, number]): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b[1] - a[1]);
  const dLon = toRad(b[0] - a[0]);
  const lat1 = toRad(a[1]);
  const lat2 = toRad(b[1]);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * R_EARTH_KM * Math.asin(Math.sqrt(h));
}

/** Percentile rank (0-100) of each value in `values` where LOWER raw = better. */
function lowerIsBetterPct(values: (number | null)[]): (number | null)[] {
  const present = values.filter((v): v is number => v !== null).sort((a, b) => a - b);
  if (present.length <= 1) return values.map((v) => (v === null ? null : 100));
  return values.map((v) => {
    if (v === null) return null;
    const below = present.filter((x) => x > v).length; // count strictly worse (larger distance)
    return (below / (present.length - 1)) * 100;
  });
}

/** Distances from every neighborhood to every pin, as direction-adjusted percentiles. */
export function pinPercentiles(
  neighborhoods: Neighborhood[],
  pins: Pin[],
): Map<string, Map<number, { pct: number | null; km: number }>> {
  const out = new Map<string, Map<number, { pct: number | null; km: number }>>();
  for (const pin of pins) {
    const dists = neighborhoods.map((n) => haversineKm(n.centroid, [pin.lon, pin.lat]));
    const pcts = lowerIsBetterPct(dists);
    const m = new Map<number, { pct: number | null; km: number }>();
    neighborhoods.forEach((n, i) => m.set(n.id, { pct: pcts[i], km: dists[i] }));
    out.set(pin.id, m);
  }
  return out;
}

function criterionMetrics(bundle: Bundle, criterion: Criterion): string[] {
  return Object.entries(bundle.metricsMeta)
    .filter(([key, meta]) => meta.criterion === criterion && bundle.cityMedians[key] != null)
    .map(([key]) => key);
}

export interface ScoreInput {
  bundle: Bundle;
  weights: Weights;
  pins: Pin[];
  filters: Filter[];
}

export function scoreAll(input: ScoreInput): ScoredNeighborhood[] {
  const { bundle, weights, pins, filters } = input;
  const pinPcts = pinPercentiles(bundle.neighborhoods, pins);

  const criteria = Object.keys(weights).filter(
    (k) => (weights[k as SliderKey] ?? 0) > 0,
  ) as SliderKey[];
  const metricsByCriterion = new Map<SliderKey, string[]>();
  for (const k of criteria) {
    if (k !== PLACES_CRITERION) {
      metricsByCriterion.set(k, criterionMetrics(bundle, k as Criterion));
    }
  }

  const scored: ScoredNeighborhood[] = bundle.neighborhoods.map((n) => {
    const explain: CriterionExplain[] = [];
    let weightedSum = 0;
    let weightTotal = 0;
    let confidenceSum = 0;
    let confidenceTotal = 0;

    for (const k of criteria) {
      const weight = weights[k] ?? 0;
      let score: number | null = null;
      let coverage = 0;
      let metricExplains: MetricExplain[] = [];

      if (k === PLACES_CRITERION) {
        if (pins.length) {
          let num = 0;
          let den = 0;
          let denAll = 0;
          metricExplains = pins.map((pin) => {
            const rec = pinPcts.get(pin.id)?.get(n.id);
            denAll += pin.weight;
            if (rec?.pct != null && pin.weight > 0) {
              num += rec.pct * pin.weight;
              den += pin.weight;
            }
            return {
              key: `pin:${pin.id}`,
              label: `Distance to ${pin.label}`,
              units: "km",
              raw: rec ? Math.round(rec.km * 10) / 10 : null,
              pct: rec?.pct ?? null,
              intraWeight: pin.weight,
              cityMedian: null,
              confidence: "high" as const,
              higherIsBetter: false,
              source: "user_pin",
              attribution: null,
            };
          });
          score = den > 0 ? num / den : null;
          coverage = denAll > 0 ? den / denAll : 0;
        }
      } else {
        const keys = metricsByCriterion.get(k) ?? [];
        let num = 0;
        let den = 0;
        let denAll = 0;
        metricExplains = keys.map((key) => {
          const meta = bundle.metricsMeta[key];
          const mv = n.metrics[key];
          denAll += meta.intraWeight;
          if (mv?.pct != null) {
            num += mv.pct * meta.intraWeight;
            den += meta.intraWeight;
          }
          return {
            key,
            label: meta.label,
            units: meta.units,
            raw: mv?.value ?? null,
            pct: mv?.pct ?? null,
            intraWeight: meta.intraWeight,
            cityMedian: bundle.cityMedians[key] ?? null,
            confidence: mv?.confidence ?? null,
            higherIsBetter: meta.higherIsBetter,
            source: meta.source,
            attribution: meta.attribution,
          };
        });
        score = den > 0 ? num / den : null;
        coverage = denAll > 0 ? den / denAll : 0;
      }

      if (score != null) {
        weightedSum += score * weight;
        weightTotal += weight;
      }
      confidenceSum += coverage * weight;
      confidenceTotal += weight;

      explain.push({ criterion: k, weight, score, coverage, contribution: null, metrics: metricExplains });
    }

    const score = weightTotal > 0 ? weightedSum / weightTotal : null;
    const confidence = confidenceTotal > 0 ? confidenceSum / confidenceTotal : 0;

    // exact decomposition: contribution_k = w_k * score_k / Σ w_k(with data)
    for (const e of explain) {
      e.contribution =
        e.score != null && weightTotal > 0 ? (e.weight * e.score) / weightTotal : null;
    }

    const exclusionReasons: string[] = [];
    for (const f of filters) {
      const raw = n.metrics[f.metric]?.value;
      if (raw == null) continue; // don't exclude on missing data — surfaced via confidence
      if (f.op === "lte" && raw > f.value) {
        exclusionReasons.push(`${bundle.metricsMeta[f.metric]?.label ?? f.metric} above limit`);
      }
      if (f.op === "gte" && raw < f.value) {
        exclusionReasons.push(`${bundle.metricsMeta[f.metric]?.label ?? f.metric} below limit`);
      }
    }

    return {
      id: n.id,
      slug: n.slug,
      name: n.name,
      score,
      confidence,
      rank: null,
      excluded: exclusionReasons.length > 0,
      exclusionReasons,
      insufficientData: confidence < MIN_CONFIDENCE,
      explain,
    };
  });

  const rankable = scored
    .filter((s) => !s.excluded && !s.insufficientData && s.score != null)
    .sort((a, b) => b.score! - a.score!);
  rankable.forEach((s, i) => (s.rank = i + 1));

  return scored.sort((a, b) => {
    if (a.rank != null && b.rank != null) return a.rank - b.rank;
    if (a.rank != null) return -1;
    if (b.rank != null) return 1;
    return (b.score ?? -1) - (a.score ?? -1);
  });
}
