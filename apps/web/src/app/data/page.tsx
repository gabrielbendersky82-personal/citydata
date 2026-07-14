import Link from "next/link";

const SOURCES = [
  ["Crime", "City of Chicago Data Portal (Socrata)", "Point-level reported incidents, rolling 3-year window, normalized per 1,000 residents/yr. Reporting practices differ between cities — scores never compare across cities."],
  ["Home values & rents", "Zillow Research (ZHVI, ZORI)", "ZIP-level series apportioned to census tracts via the HUD ZIP–tract crosswalk. Data © Zillow; displayed and derived analytics only."],
  ["Socioeconomics & housing baseline", "U.S. Census Bureau, ACS 5-year", "Tract estimates carry margins of error; high-uncertainty values are flagged. 1–2 year publication lag."],
  ["Schools", "Urban Institute Education Data API (NCES CCD, EDFacts)", "School locations, enrollment, and proficiency midpoints. Proficiency is a narrow proxy — visit schools, talk to parents."],
  ["Walkability & amenities", "Overture Maps places (includes Foursquare OS Places; © OpenStreetMap contributors)", "Counts within an 800m (≈10-min) straight-line walk of each neighborhood's center — not network distance."],
  ["Transit", "CTA GTFS static feed", "Stop density and scheduled weekly departures per km²."],
  ["Health & environment", "CDC PLACES", "Modeled small-area estimates of health measures — not direct measurements."],
  ["Natural hazards", "FEMA National Risk Index; FEMA NFHL flood zones", "Composite tract risk scores and share of area in a 1%-annual-chance flood zone. Regulatory zones ≠ forward-looking risk."],
  ["Geography", "U.S. Census TIGER/CB; City of Chicago community areas", "Tract metrics roll up to neighborhoods through a population-weighted crosswalk (2020 census blocks)."],
] as const;

export default function DataPage() {
  return (
    <main className="max-w-2xl mx-auto p-8">
      <Link href="/" className="text-sm underline" style={{ color: "var(--accent)" }}>← citydata</Link>
      <h1 className="text-2xl font-bold mt-3 mb-2" style={{ color: "var(--ink-1)" }}>Data & methodology</h1>

      <h2 className="font-semibold mt-6 mb-1" style={{ color: "var(--ink-1)" }}>How scoring works</h2>
      <p className="text-sm leading-relaxed" style={{ color: "var(--ink-2)" }}>
        Every metric is converted to a percentile <em>within the selected city</em> (100 = best), with direction
        applied (lower crime = better, higher walkability = better). Your sliders weight eight criteria plus
        your own pinned places; the fit score is the weighted average, and each neighborhood&apos;s detail view
        shows the exact contribution of every criterion and the raw values behind it. Missing data never counts
        as zero — weights renormalize over what exists, and coverage is shown as a confidence badge. Hard limits
        exclude rather than rank.
      </p>

      <h2 className="font-semibold mt-6 mb-2" style={{ color: "var(--ink-1)" }}>Sources & attribution</h2>
      <div className="space-y-3">
        {SOURCES.map(([what, source, note]) => (
          <div key={what} className="text-sm">
            <span className="font-medium" style={{ color: "var(--ink-1)" }}>{what}</span>
            <span style={{ color: "var(--ink-2)" }}> — {source}</span>
            <p className="text-xs mt-0.5" style={{ color: "var(--ink-muted)" }}>{note}</p>
          </div>
        ))}
      </div>

      <h2 className="font-semibold mt-6 mb-1" style={{ color: "var(--ink-1)" }}>Honest limits</h2>
      <ul className="text-sm list-disc pl-5 space-y-1" style={{ color: "var(--ink-2)" }}>
        <li>Public data has gaps, lags, and reporting quirks; some metrics are modeled estimates.</li>
        <li>Percentiles compare within one city only — a 90 in Chicago says nothing about Austin.</li>
        <li>Walk and pin distances are straight-line, not routes.</li>
        <li>This is decision support, not financial, legal, or safety advice. Visit in person; verify everything independently.</li>
      </ul>

      <p className="mt-6 text-xs" style={{ color: "var(--ink-muted)" }}>
        Basemap © OpenStreetMap contributors, tiles by OpenFreeMap. Housing data © Zillow.
        POI data © Overture Maps Foundation (CDLA-Permissive-2.0), including Foursquare OS Places.
      </p>
    </main>
  );
}
