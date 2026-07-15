# citydata — neighborhood fit, explained

Pick a city, set what you care about (safety, rent, schools, walkability, transit,
health, hazards, your own pinned places), and get a transparent ranking of every
neighborhood — every score decomposes exactly into the criteria behind it.
Currently live: **Chicago** (77 community areas). Master plan: `docs/PLAN.md`.

## Layout

```
apps/web/          Next.js 16 app (App Router, TS, Tailwind, MapLibre, Zustand)
  public/bundles/  Prebuilt per-city data bundles — the app serves these statically
  scripts/         Playwright e2e smoke (node scripts/e2e-smoke.mjs)
etl/               Python ETL (uv): sources → local PostGIS → percentiles → bundle
supabase/          SQL migrations (reference tables + RLS'd user tables)
.github/workflows/ etl.yml — weekly + dispatchable full refresh with full egress
docs/              PLAN.md (master plan), data-sources.md (ToS register)
```

## Running the app

```bash
pnpm install
pnpm dev          # http://localhost:3000 — works with the committed bundle, no DB needed
pnpm test         # scoring engine fixture tests (vitest)
```

Auth + saved profiles light up when `NEXT_PUBLIC_SUPABASE_URL` /
`NEXT_PUBLIC_SUPABASE_ANON_KEY` are set (see `.env.example`); the core app is
fully functional without them.

## Running the ETL

Local (needs Postgres 16 + PostGIS, `ETL_DATABASE_URL`, defaults to
`postgresql://etl:etl@localhost/citydata_etl`):

```bash
cd etl && uv sync
uv run python -m etl catalog          # metric definitions
uv run python -m etl geo-spine        # tracts, blocks, neighborhoods
uv run python -m etl crosswalk        # block-population-weighted rollup weights
uv run python -m etl crime|zillow|fema-nri|cdc-places|nfhl|schools|gtfs|pois|walkability|acs
uv run python -m etl percentiles && uv run python -m etl bundle && uv run python -m etl export
```

Every job is idempotent (re-runs are no-ops) and records a `dataset_versions`
row. The bundle lands in `apps/web/public/bundles/<city>.json`; Supabase
upsert SQL lands in `etl/out/supabase/`.

**Scheduled refresh** runs in GitHub Actions (`etl.yml`, weekly + manual
dispatch): the runner has full egress, uses official sources and true 2020
block weighting, and commits the refreshed bundle + exports back to the branch.

### Secrets (GitHub → Settings → Secrets → Actions)

| Secret | Needed for | Where to get it |
|---|---|---|
| `CENSUS_API_KEY` | ACS socioeconomics/housing metrics (only blocking one) | free at api.census.gov/data/key_signup.html |
| `SOCRATA_APP_TOKEN` | polite crime-API rate limits (optional) | free at any Socrata portal |
| `HUD_API_TOKEN` | residential-ratio ZIP↔tract crosswalk (optional; Census area-ratio fallback used otherwise) | free at huduser.gov |

## Deploying

Import this repo in Vercel (vercel.com/new), set **Root Directory** to
`apps/web`, and deploy — no env vars required (the app serves the committed
data bundle statically). Every ETL refresh commit then auto-deploys.
Optionally add `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`
to enable accounts/saved profiles once the Supabase project exists
(migrations in `supabase/migrations/`, data loads in `etl/out/supabase/`).

## Data & scoring in one paragraph

All authoritative metrics are stored at census-tract level and rolled up to
neighborhoods through a 2020-census-block population-weighted crosswalk;
point data (crime, POIs, stops, schools) aggregates into neighborhood polygons
directly. Each metric becomes a within-city percentile (100 = best,
direction-adjusted). The client computes a weighted sum over the user's
criterion sliders — missing data renormalizes weights and surfaces as a
confidence badge, never a silent zero; hard limits exclude rather than rank.
See `/data` in the app and `docs/data-sources.md` for sources, attribution,
and honest limits.
