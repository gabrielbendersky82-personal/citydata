-- User-facing tables. Supabase-only (references auth.users / auth.uid()).
create table if not exists profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  home_city smallint references cities(id),
  created_at timestamptz not null default now()
);

create table if not exists weight_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  city_id smallint references cities(id),
  name text not null,
  weights jsonb not null,
  filters jsonb not null default '{}'::jsonb,
  pins jsonb not null default '[]'::jsonb,   -- [{label, address, lon, lat, weight}]
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists weight_profiles_user_idx on weight_profiles (user_id);

create table if not exists pinned_places (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  label text not null,
  address text,
  lon double precision not null,
  lat double precision not null,
  created_at timestamptz not null default now()
);
create index if not exists pinned_places_user_idx on pinned_places (user_id);

create table if not exists shortlists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  city_id smallint not null references cities(id),
  neighborhood_ids integer[] not null default '{}',
  notes jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists shortlists_user_idx on shortlists (user_id);

alter table profiles enable row level security;
alter table weight_profiles enable row level security;
alter table pinned_places enable row level security;
alter table shortlists enable row level security;

drop policy if exists "own rows" on profiles;
create policy "own rows" on profiles for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "own rows" on weight_profiles;
create policy "own rows" on weight_profiles for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "own rows" on pinned_places;
create policy "own rows" on pinned_places for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "own rows" on shortlists;
create policy "own rows" on shortlists for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
