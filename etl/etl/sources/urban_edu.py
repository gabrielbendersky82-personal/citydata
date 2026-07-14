"""Schools via the Urban Institute Education Data API (CCD directory +
EDFacts proficiency). Produces neighborhood school-access and proficiency
metrics from school points; no key required. ODC-BY attribution."""
from __future__ import annotations

import os

import requests

from etl import db
from etl.config import load_city
from etl.fetch import UA

BASE = "https://educationdata.urban.org/api/v1"
CCD_YEAR = os.environ.get("CCD_YEAR", "2022")
EDFACTS_YEAR = os.environ.get("EDFACTS_YEAR", "2020")


def paged(url: str, params: dict) -> list[dict]:
    out: list[dict] = []
    while url:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=120)
        r.raise_for_status()
        payload = r.json()
        out.extend(payload["results"])
        url, params = payload.get("next"), {}
    return out


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]
    state_fips = int(cfg["city"]["state_fips"])
    county5 = cfg["city"]["county_fips"]

    schools = paged(f"{BASE}/schools/ccd/directory/{CCD_YEAR}/", {"fips": state_fips})
    schools = [
        s for s in schools
        if s.get("county_code") and str(s["county_code"]).zfill(5) == county5
        and s.get("latitude") and s.get("longitude")
    ]
    print(f"  {len(schools)} schools in county")

    prof: dict[str, tuple[float | None, float | None]] = {}
    try:
        for rec in paged(
            f"{BASE}/schools/edfacts/assessments/{EDFACTS_YEAR}/grade-99/",
            {"fips": state_fips},
        ):
            m = rec.get("math_test_pct_prof_midpt")
            rd = rec.get("read_test_pct_prof_midpt")
            prof[str(rec.get("ncessch"))] = (
                float(m) if m not in (None, "") and float(m) >= 0 else None,
                float(rd) if rd not in (None, "") and float(rd) >= 0 else None,
            )
    except requests.RequestException as e:
        print(f"WARN: EDFacts proficiency unavailable ({e}); access metric only")

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "urban_edu", f"ccd{CCD_YEAR}_edfacts{EDFACTS_YEAR}")
        rows = []
        for s in schools:
            ncessch = str(s["ncessch"])
            pm, pr = prof.get(ncessch, (None, None))
            rows.append(
                (
                    ncessch,
                    s.get("school_name"),
                    str(s.get("school_level") or ""),
                    city_id,
                    f"SRID=4326;POINT({float(s['longitude'])} {float(s['latitude'])})",
                    int(s["enrollment"]) if s.get("enrollment") not in (None, "") and int(s["enrollment"]) >= 0 else None,
                    pm / 100 if pm is not None else None,
                    pr / 100 if pr is not None else None,
                    CCD_YEAR,
                )
            )
        db.upsert_rows(
            c, "staging.schools",
            ["ncessch", "name", "level", "city_id", "geom", "enrollment", "prof_math", "prof_read", "vintage"],
            rows, ["ncessch"],
        )

        # school_access: public schools within 1.6km of the neighborhood's centroid
        # school_proficiency: enrollment-weighted mean of (math+read)/2 within 3km
        c.execute(
            """
            with nearby as (
              select n.id as nid, s.ncessch, s.enrollment, s.prof_math, s.prof_read,
                     ST_Distance(n.centroid_pop::geography, s.geom::geography) as d
              from neighborhoods n
              join staging.schools s on s.city_id = n.city_id
              where n.city_id = %(city)s
                and ST_DWithin(n.centroid_pop::geography, s.geom::geography, 3000)
            ),
            access as (
              select nid, count(*) filter (where d <= 1600)::numeric as v from nearby group by nid
            ),
            profic as (
              select nid,
                sum(((coalesce(prof_math,0)+coalesce(prof_read,0)) /
                     nullif((prof_math is not null)::int + (prof_read is not null)::int, 0))
                    * coalesce(enrollment, 100) * 100)
                / nullif(sum(coalesce(enrollment, 100))
                    filter (where prof_math is not null or prof_read is not null), 0) as v
              from nearby group by nid
            )
            insert into neighborhood_metrics (neighborhood_id, metric_key, value, coverage, dataset_version_id)
            select n.id, m.key, coalesce(src.v, case when m.key = 'school_access' then 0 end),
                   case when m.key = 'school_access' then 1.0
                        else case when src.v is null then 0 else 1.0 end end,
                   %(vid)s
            from neighborhoods n
            cross join (values ('school_access'), ('school_proficiency')) m(key)
            left join lateral (
              select case when m.key = 'school_access'
                          then (select v from access where nid = n.id)
                          else (select v from profic where nid = n.id) end as v
            ) src on true
            where n.city_id = %(city)s
            on conflict (neighborhood_id, metric_key, dataset_version_id)
            do update set value = excluded.value, coverage = excluded.coverage
            """,
            {"city": city_id, "vid": vid},
        )
        db.finish_dataset_version(c, vid, len(rows))
        c.commit()
        print(f"urban_edu: {len(rows)} schools, metrics published")
    return 0
