-- Reference (geo) + metrics tables. Applied to Supabase AND to the local ETL
-- database (local additionally gets staging tables; see etl/etl/local_schema.sql).
create extension if not exists postgis;

create table if not exists cities (
  id smallint primary key,
  slug text not null unique,
  name text not null,
  state char(2) not null,
  place_geoid text,
  centroid geometry(Point, 4326),
  bbox geometry(Polygon, 4326),
  status text not null default 'staging' check (status in ('active', 'staging'))
);

create table if not exists tracts (
  geoid char(11) primary key,
  city_id smallint references cities(id),
  geom geometry(MultiPolygon, 4326) not null,
  aland bigint,
  awater bigint,
  pop_2020 integer
);
create index if not exists tracts_geom_gix on tracts using gist (geom);
create index if not exists tracts_city_idx on tracts (city_id);

create table if not exists neighborhoods (
  id serial primary key,
  city_id smallint not null references cities(id),
  slug text not null,
  name text not null,
  geom geometry(MultiPolygon, 4326) not null,
  geom_display geometry(MultiPolygon, 4326),
  centroid_pop geometry(Point, 4326),   -- population-weighted centroid (for distance factors)
  boundary_source text not null check (boundary_source in ('city_official', 'zillow_archive', 'osm', 'tract_fallback')),
  source_ref text,
  is_fallback_tract boolean not null default false,
  unique (city_id, slug)
);
create index if not exists neighborhoods_geom_gix on neighborhoods using gist (geom);

create table if not exists tract_neighborhood_xwalk (
  neighborhood_id integer not null references neighborhoods(id) on delete cascade,
  tract_geoid char(11) not null references tracts(geoid),
  pop_weight numeric not null,          -- share of the tract's population in this neighborhood
  block_count integer,
  built_from text not null default '2020_blocks_p1',
  primary key (neighborhood_id, tract_geoid)
);

create table if not exists zip_tract_xwalk (
  zip char(5) not null,
  tract_geoid char(11) not null,
  res_ratio numeric not null,
  vintage text not null,
  primary key (zip, tract_geoid, vintage)
);

create table if not exists dataset_versions (
  id serial primary key,
  source text not null,
  vintage_label text not null,
  retrieved_at timestamptz not null default now(),
  row_count integer,
  checksum text,
  notes text,
  unique (source, vintage_label)
);

create table if not exists metric_definitions (
  key text primary key,
  label text not null,
  description text,
  units text,
  criterion text not null check (criterion in
    ('safety','affordability','socioeconomics','schools','walkability','transit','environment','hazard')),
  higher_is_better boolean not null,
  default_intra_weight numeric not null default 1,
  source text not null,
  source_attribution text,
  methodology_url text
);

create table if not exists tract_metrics (
  tract_geoid char(11) not null references tracts(geoid),
  metric_key text not null references metric_definitions(key),
  value numeric,
  moe numeric,
  dataset_version_id integer not null references dataset_versions(id),
  primary key (tract_geoid, metric_key, dataset_version_id)
);

create table if not exists neighborhood_metrics (
  neighborhood_id integer not null references neighborhoods(id) on delete cascade,
  metric_key text not null references metric_definitions(key),
  value numeric,
  percentile numeric,                   -- 0-100 within city, direction-adjusted (100 = best)
  coverage numeric,                     -- 0-1 population-weight share of tracts with data
  confidence text check (confidence in ('high','medium','low')),
  dataset_version_id integer not null references dataset_versions(id),
  primary key (neighborhood_id, metric_key, dataset_version_id)
);

create table if not exists city_bundles (
  city_id smallint not null references cities(id),
  built_at timestamptz not null default now(),
  version_set jsonb not null,
  bundle jsonb not null,
  is_current boolean not null default false,
  primary key (city_id, built_at)
);

create table if not exists geocode_cache (
  address_norm text primary key,
  matched_address text,
  lon double precision,
  lat double precision,
  tract_geoid char(11),
  provider text not null default 'census',
  geocoded_at timestamptz not null default now()
);

-- RLS: reference data is world-readable, written only via service/ETL paths.
alter table cities enable row level security;
alter table tracts enable row level security;
alter table neighborhoods enable row level security;
alter table tract_neighborhood_xwalk enable row level security;
alter table zip_tract_xwalk enable row level security;
alter table dataset_versions enable row level security;
alter table metric_definitions enable row level security;
alter table tract_metrics enable row level security;
alter table neighborhood_metrics enable row level security;
alter table city_bundles enable row level security;
alter table geocode_cache enable row level security;

drop policy if exists "public read" on cities;
create policy "public read" on cities for select using (true);
drop policy if exists "public read" on tracts;
create policy "public read" on tracts for select using (true);
drop policy if exists "public read" on neighborhoods;
create policy "public read" on neighborhoods for select using (true);
drop policy if exists "public read" on tract_neighborhood_xwalk;
create policy "public read" on tract_neighborhood_xwalk for select using (true);
drop policy if exists "public read" on zip_tract_xwalk;
create policy "public read" on zip_tract_xwalk for select using (true);
drop policy if exists "public read" on dataset_versions;
create policy "public read" on dataset_versions for select using (true);
drop policy if exists "public read" on metric_definitions;
create policy "public read" on metric_definitions for select using (true);
drop policy if exists "public read" on tract_metrics;
create policy "public read" on tract_metrics for select using (true);
drop policy if exists "public read" on neighborhood_metrics;
create policy "public read" on neighborhood_metrics for select using (true);
drop policy if exists "public read" on city_bundles;
create policy "public read" on city_bundles for select using (true);
drop policy if exists "public read" on geocode_cache;
create policy "public read" on geocode_cache for select using (true);
-- geocode results are a shared, non-sensitive cache; inserts come from our API route.
drop policy if exists "public insert" on geocode_cache;
create policy "public insert" on geocode_cache for insert with check (true);
