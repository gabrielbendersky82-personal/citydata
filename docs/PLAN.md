# Neighborhood-Fit Ranking App — Implementation Plan

## Context

Greenfield build in an empty repo (`citydata`). The product: a Next.js + Supabase/PostGIS web app that ranks a city's neighborhoods against user-weighted criteria (safety, affordability, schools, walkability, transit, environment, hazards, plus user-pinned proximity factors), with a transparent, explainable score, a choropleth map, and side-by-side comparison. Data comes from free/open sources wherever possible (Section 4 of the brief is treated as vetted ground truth, with endpoint re-verification scheduled in Phase 0). Stack is locked: Next.js (App Router/TS) on Vercel, Supabase (Postgres + PostGIS + Auth + RLS). This plan defines the MVP cut, resolves all Section-8 decisions, and sequences the build.

---

## (a) Recommended MVP definition

**MVP = one city done credibly (Chicago), on a nationwide-ready spine, with 9 criteria, named neighborhoods, live re-ranking, and full explainability. Two more cities (Austin, Seattle) follow immediately on the same adapter framework to prove generalization before public launch.**

### Why Chicago first
- **Best-in-class open data**: Chicago's Socrata portal has the gold-standard crime dataset (point-level, daily-updated, back to 2001, with community-area field already attached).
- **The neighborhood problem is pre-solved**: Chicago's 77 **community areas** are *official, stable, city-published polygons* that fully tile the city — we get a clean named-neighborhood layer on day one and can validate the block-weighted crosswalk against a trustworthy baseline.
- Big enough (77 areas, ~800 tracts) to stress-test performance and UX; well-known enough that scoring bugs are visually obvious ("Loop ranked #1 for quiet" = something's wrong).

### Why Austin + Seattle second (pre-launch, not post-launch)
Both are Socrata portals with official city neighborhood/GIS boundaries and strong relocation demand. Adding two cities *before* launch forces the per-city adapter pattern to be real (config, not code forks) — the single biggest architectural risk if deferred. They also diversify the hazard/climate story (flood in Austin, earthquake in Seattle, cold/lake-effect in Chicago), exercising the FEMA NRI pipeline properly.

### MVP data sources (first cut)
| Criterion | Source (MVP) | Geo level ingested |
|---|---|---|
| Public safety | City Socrata crime (per-city adapter); FBI CDE for city-level context banner | point → neighborhood |
| Affordability | Zillow ZHVI + ZORI CSVs (FREE⚠️, attribution); ACS median value/rent/rent-burden as clean baseline | ZIP + neighborhood; tract |
| Socioeconomics | Census ACS 5-yr (income, education, employment, commute time) | tract |
| Schools | Urban Institute Education Data API (locations + enrollment + proficiency) | school point → neighborhood access score |
| Walkability/amenities | OSM via Geofabrik extracts + Foursquare OS Places (Apache-2.0) — computed ourselves | POI point → density/proximity |
| Transit | GTFS static (stop density, service frequency proxy); LODES for commute-flow context | stop point → neighborhood |
| Environment/health | CDC PLACES (tract), NOAA normals (city-level context) | tract |
| Natural hazards | FEMA NRI (tract composite + per-hazard EAL), FEMA NFHL flood-zone coverage %, USGS seismic, USFS wildfire raster zonal stats | tract / polygon overlay |
| Manual factors | User pins geocoded via Census Geocoder; straight-line distance in MVP | point |

**Deliberately deferred from MVP**: live AQI (AirNow — real-time display value, not a ranking signal), drive-time/transit isochrones (Phase 2 via self-hosted OTP2/OSRM), RentCast live rents (paid), Redfin momentum metrics, First Street hazard scores (paid), BLS (county floor too coarse), state report-card school depth.

### MVP feature cut
Ships: city picker → weight sliders with 4 personas → choropleth map + ranked list → detail card with full "why" breakdown → compare (up to 4) → pinned manual factors (straight-line) → hard filters (e.g., max rent) → shareable URL config. Auth + saved profiles ship in MVP but the core flow works anonymously (auth is a conversion feature, not a gate).

Does NOT ship: nationwide coverage, isochrones, per-listing data, trends/time-series UI, mobile apps.

---

## (b) Section 8 decisions — resolved

### 1. MVP scope
**Chicago → +Austin, +Seattle before public launch. Named neighborhoods in v1** (not tracts-as-neighborhoods) — but only because we pick cities where *official* boundary files exist, making the named layer nearly free. Tracts remain the data spine and the fallback UX everywhere. Rationale: tracts-as-neighborhoods would ship faster but fails the core user journey — nobody searches "Tract 17031839100"; relocators think in named places. The compromise (official-boundary cities only) gets named UX without the boundary-curation swamp.

### 2. Neighborhood unit
**Confirmed: tract spine + named overlay + block-population-weighted crosswalk.**
- All authoritative metrics stored at tract GEOID. Neighborhood values = precomputed weighted rollups.
- Crosswalk built **offline in the Python ETL worker** (GeoPandas + PostGIS): load 2020 Census blocks with P1 population; block→tract nesting is free (GEOID prefix); block→neighborhood via `ST_Contains(neighborhood, block_centroid)`; `weight(n,t) = pop(blocks in n∩t) / pop(blocks in t)`.
- Refresh triggers: decennial census (2030), or whenever a neighborhood polygon changes (re-run per city, cheap).
- Known approximation to document: population-weighted averaging of tract *medians* (income, rent) is not a true median — acceptable for ranking; label as "weighted estimate."
- Boundary provenance order per city: **official city shapefile > Zillow archived boundaries > OSM/Who's-On-First**, recorded in a `boundary_source` field. MVP cities use official only.

### 3. Housing data
**ACS as the commercially-clean baseline + Zillow ZHVI/ZORI for current market $. Both, labeled distinctly.** ACS gives tract-level median value/rent/rent-burden with clean rights but 1–2yr lag; Zillow gives *current* dollars at ZIP and named-neighborhood granularity users actually recognize. ToS handling: "Zillow" attribution on every card/page displaying it and on the data-sources page; we display values and derived percentiles (allowed), never offer raw-data export/resale. Zillow ZIP series map to tracts via HUD ZIP↔tract crosswalk (allocation-weighted), neighborhood series matched by name with manual review per launch city. Redfin deferred to Phase 2 (adds momentum metrics, another attribution). RentCast deferred until there's a paying use case (per-address rent estimates).

### 4. Crime strategy
**Config-driven Socrata adapter framework; 3 city adapters at launch.** Each adapter is a YAML/JSON config: portal domain, dataset ID, field map (timestamp, lat/lon, category, description), and a category mapping into a common taxonomy (**violent / property / quality-of-life**, loosely NIBRS-aligned). Ingest incidents as points; aggregate directly into neighborhood polygons (crime skips the tract crosswalk — it's already sub-tract); normalize as **incidents per 1,000 residents per year over a rolling 3-year window** (population from the crosswalk rollup). Never compare absolute crime rates *across* cities in scoring (reporting practices differ) — normalization is always within-city percentile. FBI CDE supplies a city-level context line ("Chicago's overall reported crime vs national") and powers the coverage-gap banner for future cities without portals. Coverage gaps communicated via per-criterion confidence badges (see scoring spec).

### 5. Walkability
**Compute ourselves: OSM (Geofabrik extracts, ODbL) + Foursquare OS Places (Apache-2.0). No Walk Score** — its free tier is explicitly non-commercial/no-cache and premium costs recur forever. Our metric: category-weighted amenity access (grocery, restaurants/cafés, parks, pharmacies, gyms, schools, transit stops) — counts within 800m walking buffer of neighborhood population centroid + density per km², percentile-normalized. FSQ OS Places is the primary POI set (cacheable, redistributable, cleaner categories); OSM fills parks/paths and cross-checks. ODbL note: our derived scores are "produced works" (attribution required, no share-alike contamination of the whole DB) — attribute "© OpenStreetMap contributors" wherever OSM-derived data shows.

### 6. Transit/commute depth for MVP
**Shallow in MVP, honest about it**: GTFS static → stop density + weekly departures per stop (service intensity proxy) per neighborhood; LODES shown as context on detail cards (where residents commute), not scored. Pinned-address commute factor = **straight-line distance in MVP** with clear "as the crow flies" labeling. **Phase 2: self-hosted OTP2 (transit) + OSRM (drive) on a small VM** for true travel times — self-hosting avoids Mapbox/Google no-store ToS entirely, which matters because we want to precompute and cache neighborhood-centroid→pin matrices for live re-ranking. Mapbox Isochrone rejected: the no-long-term-storage clause conflicts with our precompute-everything architecture.

### 7. Geocoding
**Census Geocoder for both batch and live.** Free, no key, returns FIPS codes natively (exactly what we need to join user pins to tracts), and results are storable — no ToS friction. Wrap it in a thin `geocode()` service interface with a Geocodio driver stubbed as fallback (2,500/day free, storage allowed) for when Census Geocoder's known flakiness/downtime bites; cache every result in Postgres so each address is geocoded once. Never use Google/Mapbox geocoding (no-store).

### 8. Map/tiles vendor
**MapLibre GL JS + OpenFreeMap hosted vector tiles for MVP; migration path to self-hosted Protomaps PMTiles.** MapLibre is free/open and API-compatible with the Mapbox GL style spec. OpenFreeMap: $0, no API key, no request caps published, OSM attribution — zero setup cost. If its reliability worries us at launch, Protomaps basemap as PMTiles on object storage costs ~$0 and removes the dependency. Mapbox rejected: per-load billing, telemetry requirements, and no-store clauses on adjacent services we'd be tempted to use. The choropleth itself is **our own data**: simplified neighborhood polygons (`ST_SimplifyPreserveTopology`, ~50–100KB/city as GeoJSON) served from our API and CDN-cached — no vendor involved.

### 9. ETL runtime
**A Python ETL package run by GitHub Actions scheduled workflows, writing directly to Supabase Postgres. Not Supabase Edge Functions, not Vercel cron.** Rationale: the heavy work is geospatial batch processing (shapefile loads, block crosswalks, zonal raster stats, million-row crime backfills) — that needs GeoPandas/rasterio/GDAL, gigabytes of temp disk, and >15-min runtimes. Edge Functions (Deno, memory/time limits) and Vercel functions (bundle/time limits) can't do it; GitHub Actions gives free scheduled runners with the repo right there, secrets management, and run logs. Each job is idempotent (upsert keyed on natural key + `dataset_version`). Light *on-demand* work (geocode proxy, future AirNow) lives in Next.js route handlers with Postgres-backed caching. If jobs outgrow Actions limits (6hr/job), promote to a small Fly.io/Railway worker — same code.

### 10. Scoring math
**Weighted arithmetic sum over within-city percentile-normalized metrics.** Details in section (e). Weighted sum beats geometric mean because: it's explainable in one sentence ("your score is the weighted average of these bars"), contributions decompose exactly (geometric mean contributions don't), and it tolerates zeros/missing without blowing up. Geometric mean's advantage (punishing terrible-on-one-axis neighborhoods) is delivered instead by **hard filters** and by showing per-criterion values prominently. Normalization = percentile rank within city (robust to outliers/skew, uniform color ramps, no parametric assumptions). Missing data → weight renormalization over available criteria + visible coverage badge, never silent zeros. Hard filters exclude before ranking.

### 11. Freshness & versioning
Every ingested batch gets a row in `dataset_versions` (source, vintage label e.g. `acs_2024_5yr`, `places_2026`, retrieval date, row count, checksum). Metric rows FK to their version; the served "city bundle" pins the version set it was built from, so any score is reproducible ("scored against ACS 2020–2024, crime through 2026-06"). Cadence: crime **weekly**; Zillow **monthly**; GTFS **monthly**; ACS/PLACES/Urban Inst./NRI **annual on release** (PLACES dataset-ID looked up dynamically, never hardcoded); OSM/FSQ POIs **quarterly**; TIGER/boundaries/crosswalk **on change only**; HUD crosswalk **quarterly**. Old versions retained (metrics tables are append-by-version), enabling future trend features.

### 12. Legal/ToS register → see section (h).

---

## (c) PostGIS data model sketch

Schemas: `geo` (spatial reference data), `metrics` (ingested + derived data), `app` (user data, RLS-protected). ETL role gets write on `geo`/`metrics`; the app's anon/authed roles get read-only on those and RLS-scoped write on `app`.

```sql
-- ===== geo =====
geo.cities (
  id smallint PK, slug text UNIQUE, name text, state char(2),
  place_geoid text,             -- Census place FIPS
  centroid geometry(Point,4326), bbox geometry(Polygon,4326),
  status text                   -- 'active' | 'staging'
)

geo.tracts (
  geoid char(11) PK,            -- state+county+tract FIPS
  city_id smallint FK NULL,     -- assigned if tract intersects an active city
  geom geometry(MultiPolygon,4326),      -- CB (simplified) geometry
  aland bigint, awater bigint, pop_2020 int
)  -- GiST index on geom

geo.neighborhoods (
  id serial PK, city_id smallint FK, slug text, name text,
  geom geometry(MultiPolygon,4326),
  geom_display geometry(MultiPolygon,4326),  -- simplified for the map
  boundary_source text,         -- 'city_official' | 'zillow_archive' | 'osm'
  source_ref text, is_fallback_tract bool DEFAULT false,
  UNIQUE(city_id, slug)
)  -- GiST index on geom

geo.tract_neighborhood_xwalk (
  neighborhood_id int FK, tract_geoid char(11) FK,
  pop_weight numeric,           -- share of tract's population inside neighborhood
  block_count int, built_from text,   -- '2020_blocks_p1'
  PRIMARY KEY (neighborhood_id, tract_geoid)
)

geo.zip_tract_xwalk (zip char(5), tract_geoid char(11), res_ratio numeric, vintage text)  -- HUD

-- ===== metrics =====
metrics.dataset_versions (
  id serial PK, source text, vintage_label text, retrieved_at timestamptz,
  row_count int, checksum text, notes text, UNIQUE(source, vintage_label)
)

metrics.metric_definitions (
  key text PK,                  -- e.g. 'median_gross_rent', 'violent_crime_rate'
  label text, description text, units text,
  criterion text,               -- 'safety'|'affordability'|'socioeconomics'|'schools'|
                                -- 'walkability'|'transit'|'environment'|'hazard'
  higher_is_better bool,
  default_intra_weight numeric, -- weight within its criterion
  source text, methodology_url text
)

metrics.tract_metrics (
  tract_geoid char(11), metric_key text FK, value numeric, moe numeric NULL,
  dataset_version_id int FK,
  PRIMARY KEY (tract_geoid, metric_key, dataset_version_id)
)

metrics.neighborhood_metrics (        -- crosswalk rollups + native-granularity metrics
  neighborhood_id int FK, metric_key text FK,
  value numeric, percentile numeric,  -- within-city percentile, precomputed
  coverage numeric,                   -- 0–1: pop-weight share of tracts that had data
  confidence text,                    -- 'high'|'medium'|'low' (MOE/coverage derived)
  dataset_version_id int FK,
  PRIMARY KEY (neighborhood_id, metric_key, dataset_version_id)
)

metrics.crime_incidents (             -- partitioned by city_id
  id bigint, city_id smallint, occurred_at timestamptz,
  category text,                      -- normalized: violent|property|qol
  source_category text, geom geometry(Point,4326),
  neighborhood_id int NULL,           -- assigned at ingest via ST_Contains
  source_row_id text, dataset_version_id int,
  UNIQUE(city_id, source_row_id)
)  -- GiST on geom; BRIN on occurred_at

metrics.pois (
  id bigint PK, source text,          -- 'fsq_os' | 'osm'
  category text, name text, geom geometry(Point,4326), city_id smallint,
  dataset_version_id int
)  -- GiST on geom

metrics.geocode_cache (address_norm text PK, geom geometry(Point,4326),
                       tract_geoid char(11), provider text, geocoded_at timestamptz)

metrics.city_bundles (               -- prebuilt JSON served to the client
  city_id smallint, version_set jsonb, built_at timestamptz,
  bundle jsonb,                      -- neighborhoods × metrics × percentiles + geojson ref
  PRIMARY KEY (city_id, built_at)
)

-- ===== app (RLS: owner-only) =====
app.profiles (user_id uuid PK FK auth.users, display_name text, home_city smallint)
app.weight_profiles (id uuid PK, user_id uuid, city_id smallint, name text,
                     weights jsonb, filters jsonb, created_at timestamptz)
app.pinned_places (id uuid PK, user_id uuid, label text, address text,
                   geom geometry(Point,4326), created_at timestamptz)
app.shortlists (id uuid PK, user_id uuid, city_id smallint,
                neighborhood_ids int[], notes jsonb)
```

Notes: all geometry in 4326 for the web; use `geography` casts or a per-city projected SRID for distance math. Percentiles precomputed in `neighborhood_metrics` at bundle-build time so the client never normalizes.

---

## (d) ETL / ingestion design

**Layout**: monorepo — `apps/web` (Next.js), `etl/` (Python package, `uv`-managed: GeoPandas, Shapely, rasterio, requests, psycopg). Each pipeline is a CLI (`python -m etl.run acs --city chicago --vintage 2024`), idempotent, writing through a common `upsert_with_version()` helper.

**Orchestration**: GitHub Actions scheduled workflows (weekly crime, monthly Zillow/GTFS, quarterly POIs/HUD, manual-dispatch annual jobs). Every run: create `dataset_versions` row → extract to scratch → transform → upsert → validate (row counts, null rates, value-range assertions vs prior version; fail loudly, don't publish) → rebuild affected `neighborhood_metrics` percentiles → rebuild `city_bundles` → purge CDN cache tag.

**Per-source handling**:
| Source | Cadence | Rate-limit handling | Notes |
|---|---|---|---|
| TIGER/CB boundaries | on change | bulk file download | tracts, blocks, places; CB files for display |
| City neighborhood shapefiles | on change | bulk | provenance recorded |
| Crosswalk build | after any boundary change | local compute | blocks + P1 pop; validation: weights sum to ~1 per tract |
| Census ACS | annual | key required (2026); chunk variable lists; batch by county | fetch `_M` MOE vars alongside estimates |
| Socrata crime | weekly incremental | X-App-Token; `$where updated_at > last_run`, `$limit/$offset` pages of 50k | per-city config; full backfill once |
| Zillow ZHVI/ZORI | monthly | CSV download, no API | name-match neighborhoods per city (manual review file) |
| HUD FMR + ZIP xwalk | quarterly | bearer token | |
| FEMA NRI | annual/on release | bulk download (post-RAPT: **re-verify endpoint in Phase 0**) | tract table |
| FEMA NFHL | annual | ArcGIS REST, per-city bbox queries, layer 28 | compute % of neighborhood in SFHA zones |
| USGS seismic / USFS wildfire | on release | bulk raster; zonal stats in rasterio | |
| CDC PLACES | annual | Socrata; **resolve dataset ID dynamically** via catalog search | |
| Urban Institute education | annual | paginate 10k/page, no key | schools + proficiency |
| GTFS static | monthly | Mobility Database catalog → agency zips | stop density/frequency |
| Geofabrik OSM + FSQ OS Places | quarterly | bulk extracts (osmium filter) | POI table refresh |
| LODES | annual | bulk CSV | context display only |
| Census Geocoder (live) | on-demand | proxy route + `geocode_cache`; batch endpoint for bulk | Geocodio fallback driver |

**Precompute vs live**: everything scoreable is precomputed into `neighborhood_metrics` (value + percentile + coverage) and packaged into `city_bundles`. Live paths are only: geocoding a new pin, distance calc to pins (client-side haversine in MVP), and auth/CRUD.

---

## (e) Scoring engine spec

**Two-level model**: ~9 **criteria** (user-facing sliders) each composed of **metrics** with fixed default intra-weights (adjustable in advanced mode).

Criteria: Safety · Affordability · Socioeconomics · Schools · Walkability & Amenities · Transit · Environment & Health · Natural-Hazard Risk · My Places (manual pins).

1. **Normalization** (server, at bundle build): for each metric m and neighborhood n in city c: `pct(n,m) = percentile rank of value(n,m) among c's neighborhoods`, flipped when `higher_is_better = false`, so 100 = best within the city. Raw value, city median, and percentile all shipped in the bundle.
2. **Criterion score** (client): `C_k(n) = Σ_m intra_w_m · pct(n,m) / Σ_m intra_w_m` over metrics *with data*; `coverage_k(n) = Σ available intra_w / Σ all intra_w`.
3. **Overall fit** (client, live): user weights `u_k ∈ [0,5]` → `Fit(n) = Σ_k u_k · C_k(n) / Σ_k u_k` over criteria with `coverage_k > 0`. Slider changes are pure arithmetic over the in-memory bundle — re-rank in <16ms for hundreds of neighborhoods.
4. **Missing data**: renormalize (steps 2–3) — never impute zero. Overall `confidence(n) = Σ_k u_k·coverage_k / Σ_k u_k`; below 0.6, the neighborhood is shown greyed with "insufficient data for your priorities" instead of a rank.
5. **MOE**: ACS metrics with CV > 30% (`CV = (MOE/1.645)/estimate`) are marked low-confidence; they still score but the badge and detail card disclose it.
6. **Hard filters**: predicates on raw values (e.g., `zori_rent ≤ 2000`, `flood_sfha_pct < 20`), applied before ranking; excluded neighborhoods stay on the map hatched/grey with the reason.
7. **Manual factors**: pin → geocode → distance from neighborhood population centroid → normalized within city by percentile of (–distance). Each pin is a sub-metric of "My Places" with its own slider. Phase 2 swaps distance for OTP2/OSRM travel time.
8. **Explainability payload** (per neighborhood, powers the "why" UI): for every criterion and metric — raw value, units, city median, percentile, weight applied, contribution points to total, source + vintage, confidence. Total is exactly the sum of contributions.
9. **Persona presets**: 4 weight vectors (Families, Young professional, Budget-first, Retiree) stored as seed rows; selecting one just sets sliders — fully user-editable after.

---

## (f) Frontend architecture & key screens

- **State**: city bundle fetched once (SWR, CDN-cached, immutable per version-set); weights/filters/pins in a Zustand store; scoring is a pure selector over (bundle × store). URL encodes weights/filters/pins (compressed query param) → shareable configs without auth.
- **Map**: MapLibre GL, OpenFreeMap basemap, our neighborhood GeoJSON as a fill layer colored by live score (feature-state updates, no re-fetch on slider move). Hover → tooltip; click → detail panel. Pins rendered as markers.
- **Screens**:
  1. `/` — city picker (active cities + "request a city" capture).
  2. `/{city}` — the app: left rail = persona chips + criterion sliders + filters + pins manager; center = choropleth; right = live-ranked list with score bars and confidence badges.
  3. `/{city}/n/{slug}` (also as slide-over) — detail: score breakdown table (the explainability payload rendered as stacked contribution bars), per-criterion raw stats vs city median, crime mix, amenity counts, hazard panel, LODES commute context, data-vintage footnotes, "verify independently" framing.
  4. `/{city}/compare?ids=…` — up to 4 side-by-side columns.
  5. `/account` — saved weight profiles, pins, shortlists (Supabase Auth; magic link + OAuth).
  6. `/data` — sources, vintages, methodology, attributions (Zillow, OSM, OpenFreeMap, FSQ), disclaimers.
- **API routes** (Next.js route handlers): `GET /api/cities`, `GET /api/cities/{city}/bundle`, `GET /api/cities/{city}/neighborhoods/{id}`, `POST /api/geocode` (proxy + cache). User CRUD goes straight through the Supabase client under RLS.
- Bundles served with cache tags; ETL purges on publish.

---

## (g) Phased roadmap

**Phase 0 — Foundations & verification (short)**
Scaffold monorepo (Next.js app, `etl/` package, CI), Supabase project with PostGIS + schemas/roles/RLS shells, provision all keys (Census, api.data.gov, Socrata tokens, HUD, NOAA, AirNow), and **re-verify the endpoints/pricing the brief flags**: FEMA NRI post-RAPT download location, Census key enforcement, Transitland/Mapbox pricing (informational), OpenFreeMap ToS. Draft ToS register (h) into `/docs`.
*DoD: `pnpm dev` serves a stub app; `python -m etl.run smoke` writes/reads Supabase; all keys in secrets; verification memo committed.*

**Phase 1 — Geo spine (Chicago)**
Load tracts/blocks/place boundaries + Chicago community areas; build & validate block-weighted crosswalk (weights sum ≈1 per covered tract; spot-check 5 areas against city population figures); simplified display geometries.
*DoD: SQL query returns any tract metric rolled up to all 77 community areas with coverage stats.*

**Phase 2 — Metrics ingestion (Chicago)**
ACS (+MOE), Zillow, crime backfill + weekly incremental, FEMA NRI/NFHL, PLACES, USGS/USFS, Urban Institute schools, GTFS, OSM+FSQ POIs and walkability computation; `dataset_versions` + validation gates live; percentile build + first `city_bundle`.
*DoD: every metric in the catalog populated for ≥95% of community areas (or explicitly coverage-flagged); bundle JSON validates against schema; re-running any job is a no-op.*

**Phase 3 — Scoring engine + API**
Metric catalog with directions/intra-weights; bundle endpoint; client scoring lib (pure functions, unit-tested against hand-computed fixtures); persona presets; explainability payload.
*DoD: scoring lib passes fixture tests incl. missing-data renormalization and filter exclusion; slider→re-rank under 16ms on a 77-neighborhood bundle.*

**Phase 4 — Frontend MVP (Chicago)**
Screens 1–3 + compare; choropleth with live recolor; detail explainability UI; hard filters; shareable URLs; `/data` page with attributions/disclaimers.
*DoD: a user can pick Chicago, set weights, see ranked map+list update live, open a detail card showing the full "why," compare 3 areas, share a URL that reproduces their config.*

**Phase 5 — Manual factors + auth**
Geocode proxy + cache; pins with per-pin weights (straight-line); Supabase Auth; saved weight profiles/pins/shortlists under RLS.
*DoD: signed-in user pins two addresses, weights them, ranking reflects proximity; profile persists across sessions; RLS verified (user A cannot read user B).*

**Phase 6 — Generalize: Austin + Seattle**
City onboarding runbook; crime adapter configs; official neighborhood boundaries + crosswalks; Zillow name-matching review; full pipeline + bundles for both.
*DoD: both cities live end-to-end with no code forks — only config + data review; onboarding runbook accurate enough that a new city is ~days, not weeks.*

**Phase 7 — Harden & launch**
Monitoring/alerting on ETL failures and staleness; Lighthouse/perf pass; SEO per-city pages; legal review of disclaimers; error states for coverage gaps.
*DoD: public launch checklist green; an ETL failure pages us; stale data (>cadence×2) shows a UI notice.*

**Post-MVP backlog (ordered)**: OTP2/OSRM travel-time factors → more cities (portal-first expansion) → Redfin momentum + AirNow live AQI display → tracts-as-neighborhoods fallback mode for non-portal cities (national breadth) → RentCast / First Street paid upgrades → trends over versions.

---

## (h) Risk & ToS register

**ToS/compliance:**
| Source | Obligation | Our compliance |
|---|---|---|
| Zillow research CSVs | Attribution; no raw resale | "© Zillow" on cards + /data; display/derived only; no export |
| Redfin (P2) | Attribution; downloads only | Same pattern; no scraping |
| OSM/Geofabrik (ODbL) | Attribution; share-alike on derivative DBs | Attribute everywhere shown; scores are produced works; keep OSM-derived tables isolated |
| FSQ OS Places | Apache-2.0 attribution | /data page |
| OpenFreeMap tiles | OSM attribution | Map attribution control |
| Census/ACS/TIGER, FEMA, CDC, USGS, USFS, HUD, Urban Inst. (ODC-By) | Public domain / attribution | /data page citations |
| Socrata portals | Per-portal terms; app token | Cite each portal; respect rate limits |
| Walk Score, Google/Mapbox geocode, Zillow Bridge, Realtor RapidAPI | No-cache / no-store / high risk | **Not used, by decision** |

**Top risks & mitigations:**
1. **Socrata schema drift / dataset retirement** — validation gates fail loudly; adapters are config; staleness surfaces in UI rather than silently serving old data.
2. **Zillow neighborhood-name mismatch** with our polygons — per-city manual match review file; unmatched areas fall back to ZIP-crosswalked values with coverage flag.
3. **FEMA NRI endpoint churn (RAPT consolidation)** — Phase 0 re-verification; treat as bulk annual file, keep a vendored copy.
4. **Score credibility** (esp. schools, crime interpretation) — explainability-first UI, confidence badges, "decision support, verify independently" framing everywhere; school metrics labeled as proficiency/enrollment facts, never a single "school grade."
5. **Cross-city comparability trap** — scoring is strictly within-city; UI never shows cross-city score comparisons.
6. **Bundle size / map perf** — simplified geometries, percentiles precomputed, feature-state recoloring; budget: bundle <1.5MB gzipped/city.
7. **GitHub Actions limits** for big backfills — chunked jobs; promote to a small worker VM if needed (same Python code).
8. **Census Geocoder flakiness** — cache-first + Geocodio fallback driver.
9. **Fair-housing adjacency**: ranking neighborhoods on demographics can drift toward steering. Mitigation: score on *outcomes users choose* (affordability, safety, access), never race/ethnicity composition; show demographic facts descriptively only; note for legal review in Phase 7.
10. **Cost drivers** are near-zero by design (Supabase Pro ~$25/mo, Vercel Pro ~$20/mo, everything else $0); the first real costs appear only at post-MVP upgrades (worker VM for OTP2, RentCast, First Street).

---

## (i) Open questions for you

1. **City choice**: any personal preference or user-demand signal that should override Chicago/Austin/Seattle (e.g., a city you're relocating to and can dogfood)?
2. **Budget ceiling**: is ~$50/mo (Supabase + Vercel) the target, and is a small worker VM (~$10–20/mo) acceptable in Phase 2 for OTP2/OSRM?
3. **Timeline/effort**: is there a launch date or is this pace-agnostic? (Affects whether Austin+Seattle stay pre-launch or slip post-launch.)
4. **Monetization intent**: any plan to charge? (Locks in some ToS choices — e.g., Zillow display-only is fine, Walk Score would remain off the table.)
5. **Anonymous-first OK?**: I've planned the core flow to work without sign-in (auth only for saving). Confirm that matches your intent.
6. **ETL in GitHub Actions**: comfortable with pipelines running in this repo's Actions (secrets in GH), or do you want everything inside Supabase/Vercel even at the cost of capability?
7. **Brand/domain**: any name/domain decided? (Affects SEO city pages in Phase 7, nothing earlier.)
