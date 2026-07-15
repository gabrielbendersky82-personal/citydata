# Data source & ToS register

Per master plan §h. Every source, its obligations, and how we comply.
Legend: FREE = free & commercially usable · FREE⚠️ = free with ToS constraints.

| Source | License/terms | Obligations | Compliance |
|---|---|---|---|
| City Socrata portals (crime) | FREE (open data) | per-portal terms; app token courtesy | portal cited on /data; `SOCRATA_APP_TOKEN` supported; within-city normalization only |
| U.S. Census (ACS, TIGER, blocks, ZCTA rel files, geocoder) | FREE (public domain) | none (attribution courteous) | cited on /data; API key used for ACS |
| Zillow Research CSVs (ZHVI/ZORI) | FREE⚠️ | attribution "Zillow"; no raw resale/redistribution | "© Zillow" on /data + detail cards; only derived percentiles + displayed values; no export endpoints |
| FEMA NRI / NFHL / OpenFEMA | FREE (public domain) | citation | cited on /data; NRI URL re-verified per release (scraped discovery) |
| CDC PLACES | FREE (public domain) | citation; modeled-estimate caveat | cited + "modeled estimates" caveat on /data |
| Urban Institute Education Data API | FREE (ODC-BY) | attribution | cited on /data |
| CTA GTFS | FREE (open) | terms of feed use | cited; schedule-derived aggregates only |
| Overture Maps places (incl. Foursquare OS Places, OSM-derived) | FREE (CDLA-Permissive-2.0; ODbL components) | attribution; OSM attribution | "© Overture Maps Foundation / Foursquare OS Places / © OpenStreetMap contributors" on /data + map |
| OpenFreeMap tiles | FREE | OSM attribution | attribution control on every map |
| HUD USPS crosswalk (optional) | FREE | token; cite | cited when used |

## Deliberately NOT used (decision, not oversight)

- **Walk Score** — free tier is non-commercial, no-cache, mandatory branding; we compute walkability ourselves.
- **Google / Mapbox geocoding & isochrones** — no-store clauses conflict with our precompute-and-cache architecture; Census Geocoder + (Phase 2) self-hosted OTP2/OSRM instead.
- **Zillow Bridge API** — no-local-storage rule.
- **Realtor.com RapidAPI wrappers** — unofficial scrapers, high legal risk.
- **EPA EJScreen** — removed from federal web in 2025; no official API.

## Cross-city comparability guardrail

Crime reporting practices, portal coverage, and metric availability differ by
city. All percentiles are computed **within one city**; the product never
displays cross-city score comparisons.

## Known approximations (also surfaced in-app)

- Tract medians (income, rent) roll up to neighborhoods as population-weighted
  means — labeled "weighted estimate".
- Walk/pin distances are straight-line, not network routes (OTP2/OSRM planned).
- ZIP→tract apportionment uses HUD residential ratios when a token is
  configured, else Census ZCTA land-area shares (vintage-flagged).
- ACS estimates carry margins of error; CV > 30% marks a metric low-confidence.
