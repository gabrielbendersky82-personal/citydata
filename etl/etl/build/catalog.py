"""Metric catalog: every scoreable metric, its criterion, direction, and
default intra-criterion weight. Seeded into metric_definitions (idempotent).
"""
from __future__ import annotations

from etl import db

# key, label, units, criterion, higher_is_better, intra_weight, source, attribution
METRICS: list[tuple[str, str, str, str, bool, float, str, str]] = [
    # --- safety (crime normalized per 1k residents/yr; density fallback flagged in notes) ---
    ("violent_crime_rate", "Violent crime", "per 1k residents/yr", "safety", False, 3, "socrata_crime", "City of Chicago Data Portal"),
    ("property_crime_rate", "Property crime", "per 1k residents/yr", "safety", False, 2, "socrata_crime", "City of Chicago Data Portal"),
    ("qol_crime_rate", "Quality-of-life offenses", "per 1k residents/yr", "safety", False, 1, "socrata_crime", "City of Chicago Data Portal"),
    # --- affordability ---
    ("zhvi", "Typical home value (ZHVI)", "USD", "affordability", False, 2, "zillow", "Zillow"),
    ("zori", "Typical asking rent (ZORI)", "USD/mo", "affordability", False, 3, "zillow", "Zillow"),
    ("median_home_value", "Median home value (ACS)", "USD", "affordability", False, 1, "acs", "U.S. Census Bureau ACS"),
    ("median_gross_rent", "Median gross rent (ACS)", "USD/mo", "affordability", False, 2, "acs", "U.S. Census Bureau ACS"),
    ("rent_burden_pct", "Renters spending 30%+ on rent", "%", "affordability", False, 2, "acs", "U.S. Census Bureau ACS"),
    # --- socioeconomics ---
    ("median_hh_income", "Median household income", "USD", "socioeconomics", True, 3, "acs", "U.S. Census Bureau ACS"),
    ("poverty_rate", "Poverty rate", "%", "socioeconomics", False, 2, "acs", "U.S. Census Bureau ACS"),
    ("bachelors_plus_pct", "Bachelor's degree or higher", "%", "socioeconomics", True, 2, "acs", "U.S. Census Bureau ACS"),
    ("unemployment_rate", "Unemployment rate", "%", "socioeconomics", False, 2, "acs", "U.S. Census Bureau ACS"),
    ("mean_commute_min", "Mean commute time", "min", "socioeconomics", False, 1, "acs", "U.S. Census Bureau ACS"),
    # --- schools ---
    ("school_access", "Public schools within 1.6km", "schools", "schools", True, 1, "urban_edu", "Urban Institute Education Data"),
    ("school_proficiency", "Nearby school proficiency", "% proficient", "schools", True, 2, "urban_edu", "Urban Institute Education Data"),
    # --- walkability ---
    ("essential_amenities_800m", "Essentials within a 10-min walk", "places", "walkability", True, 3, "overture_places", "Overture Maps / Foursquare OS Places"),
    ("food_venues_800m", "Food & drink within a 10-min walk", "places", "walkability", True, 2, "overture_places", "Overture Maps / Foursquare OS Places"),
    ("amenity_density", "Overall amenity density", "places/km²", "walkability", True, 2, "overture_places", "Overture Maps / Foursquare OS Places"),
    ("park_access", "Parks & green space nearby", "places", "walkability", True, 2, "overture_places", "Overture Maps / Foursquare OS Places"),
    # --- transit ---
    ("stop_density", "Transit stops per km²", "stops/km²", "transit", True, 2, "gtfs", "CTA GTFS"),
    ("weekly_departures", "Weekly transit departures nearby", "departures", "transit", True, 3, "gtfs", "CTA GTFS"),
    # --- environment & health ---
    ("poor_mental_health_pct", "Frequent mental distress (adults)", "%", "environment", False, 1, "cdc_places", "CDC PLACES"),
    ("asthma_pct", "Adult asthma prevalence", "%", "environment", False, 1, "cdc_places", "CDC PLACES"),
    ("physical_inactivity_pct", "Physical inactivity (adults)", "%", "environment", False, 1, "cdc_places", "CDC PLACES"),
    ("life_expectancy", "Life expectancy at birth", "years", "environment", True, 2, "cdc_places", "CDC PLACES"),
    # --- natural hazard ---
    ("nri_risk_score", "FEMA composite risk index", "score", "hazard", False, 3, "fema_nri", "FEMA National Risk Index"),
    ("flood_sfha_pct", "Area in FEMA flood zone", "%", "hazard", False, 2, "nfhl", "FEMA NFHL"),
    ("nri_heat_score", "Extreme heat risk", "score", "hazard", False, 1, "fema_nri", "FEMA National Risk Index"),
    ("nri_winter_score", "Winter weather risk", "score", "hazard", False, 1, "fema_nri", "FEMA National Risk Index"),
    ("nri_tornado_score", "Tornado risk", "score", "hazard", False, 1, "fema_nri", "FEMA National Risk Index"),
]


def seed(c) -> int:
    return db.upsert_rows(
        c,
        "metric_definitions",
        ["key", "label", "units", "criterion", "higher_is_better", "default_intra_weight", "source", "source_attribution"],
        METRICS,
        ["key"],
    )


def run(city: str, extra: list[str]) -> int:
    with db.conn() as c:
        db.apply_schema(c)
        n = seed(c)
        c.commit()
    print(f"metric catalog seeded: {n} metrics")
    return 0
