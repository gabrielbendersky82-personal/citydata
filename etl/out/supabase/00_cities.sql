-- cities: 1 rows (generated; idempotent)
insert into cities (id, slug, name, state, place_geoid, status) values
(1, 'chicago', 'Chicago', 'IL', '1714000', 'staging')
on conflict (id) do update set slug = excluded.slug, name = excluded.name, state = excluded.state, place_geoid = excluded.place_geoid, status = excluded.status;
