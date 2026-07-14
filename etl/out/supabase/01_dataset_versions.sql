-- dataset_versions: 5 rows (generated; idempotent)
insert into dataset_versions (id, source, vintage_label, retrieved_at, row_count, checksum, notes) values
(1, 'smoke', 'v0', '2026-07-14 22:57:35.282986+00:00', 0, null, 'smoke test'),
(6, 'geo_spine', 'chicago_tiger_blocks2020', '2026-07-14 23:12:48.508736+00:00', 1408, null, ''),
(7, 'crosswalk', 'chicago_area_fallback', '2026-07-14 23:13:56.591600+00:00', 820, null, ''),
(8, 'overture_places', '2026-06-17.0', '2026-07-14 23:21:45.442389+00:00', 41558, null, ''),
(10, 'walkability', 'chicago_pois_800m', '2026-07-14 23:23:14.103964+00:00', 308, null, '')
on conflict (source, vintage_label) do update set id = excluded.id, retrieved_at = excluded.retrieved_at, row_count = excluded.row_count, checksum = excluded.checksum, notes = excluded.notes;
select setval('dataset_versions_id_seq', (select coalesce(max(id), 1) from dataset_versions));
