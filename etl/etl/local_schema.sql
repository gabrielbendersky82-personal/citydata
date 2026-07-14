-- Local-only staging tables (never loaded to Supabase): raw spatial data too
-- heavy for the serving database. Applied after supabase/migrations/0001_reference.sql.
create schema if not exists staging;

create table if not exists staging.blocks (
  geoid char(15) primary key,          -- 2020 tabulation block
  tract_geoid char(11) not null,
  pop integer not null default 0,
  centroid geometry(Point, 4326) not null
);
create index if not exists blocks_centroid_gix on staging.blocks using gist (centroid);
create index if not exists blocks_tract_idx on staging.blocks (tract_geoid);

create table if not exists staging.crime_incidents (
  city_id smallint not null,
  source_row_id text not null,
  occurred_at timestamptz not null,
  category text not null,              -- normalized: violent | property | qol
  source_category text,
  geom geometry(Point, 4326),
  neighborhood_id integer,
  dataset_version_id integer,
  primary key (city_id, source_row_id)
);
create index if not exists crime_geom_gix on staging.crime_incidents using gist (geom);
create index if not exists crime_time_idx on staging.crime_incidents (city_id, occurred_at);

create table if not exists staging.pois (
  id text primary key,                 -- source-prefixed id, e.g. 'fsq:...' / 'osm:node/123'
  source text not null,                -- 'fsq_os' | 'osm'
  category text not null,             -- normalized amenity bucket
  source_category text,
  name text,
  city_id smallint,
  geom geometry(Point, 4326) not null
);
create index if not exists pois_geom_gix on staging.pois using gist (geom);
create index if not exists pois_city_idx on staging.pois (city_id, category);

create table if not exists staging.schools (
  ncessch text primary key,
  name text,
  level text,                          -- elementary/middle/high/other
  city_id smallint,
  geom geometry(Point, 4326),
  enrollment integer,
  prof_math numeric,                   -- share proficient, 0-1 (EDFacts)
  prof_read numeric,
  vintage text
);

create table if not exists staging.gtfs_stops (
  stop_id text,
  agency text,
  city_id smallint,
  geom geometry(Point, 4326) not null,
  weekly_departures integer,
  primary key (agency, stop_id)
);
create index if not exists gtfs_stops_gix on staging.gtfs_stops using gist (geom);
