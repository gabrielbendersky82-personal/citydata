"""CLI dispatcher: python -m etl <job> [--city slug] [args...]"""
import argparse
import importlib
import sys

JOBS = {
    "smoke": "etl.jobs.smoke",
    "geo-spine": "etl.geo.spine",
    "crosswalk": "etl.geo.crosswalk",
    "crime": "etl.sources.socrata_crime",
    "zillow": "etl.sources.zillow",
    "fema-nri": "etl.sources.fema_nri",
    "nfhl": "etl.sources.nfhl",
    "cdc-places": "etl.sources.cdc_places",
    "schools": "etl.sources.urban_edu",
    "gtfs": "etl.sources.gtfs",
    "pois": "etl.sources.osm_fsq",
    "walkability": "etl.build.walkability",
    "acs": "etl.sources.acs",
    "percentiles": "etl.build.percentiles",
    "bundle": "etl.build.bundle",
    "export": "etl.build.supabase_loader",
}


def main() -> int:
    parser = argparse.ArgumentParser(prog="etl")
    parser.add_argument("job", choices=sorted(JOBS))
    parser.add_argument("--city", default="chicago")
    args, extra = parser.parse_known_args()
    mod = importlib.import_module(JOBS[args.job])
    return int(mod.run(city=args.city, extra=extra) or 0)


if __name__ == "__main__":
    sys.exit(main())
