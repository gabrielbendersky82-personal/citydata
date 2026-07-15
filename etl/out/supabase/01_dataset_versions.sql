-- dataset_versions: 9 rows (generated; idempotent)
insert into dataset_versions (id, source, vintage_label, retrieved_at, row_count, checksum, notes) values
(1, 'geo_spine', 'chicago_tiger_blocks2020', '2026-07-15 01:09:48.683488+00:00', 1408, null, ''),
(2, 'crosswalk', 'chicago_2020_blocks_p1', '2026-07-15 01:09:56.879616+00:00', 802, null, ''),
(3, 'socrata_crime', 'chicago_2023-07-16_w3y', '2026-07-15 01:09:57.568056+00:00', 744359, null, ''),
(5, 'cdc_places', 'tract_gis_yjkw-uj5s', '2026-07-15 01:12:30.545685+00:00', 3984, null, ''),
(6, 'nfhl', 'chicago_sfha', '2026-07-15 01:12:34.311002+00:00', 77, null, ''),
(7, 'urban_edu', 'ccd2022_edfacts2020', '2026-07-15 01:12:50.700090+00:00', 1415, null, ''),
(8, 'gtfs', 'chicago_static', '2026-07-15 01:12:51.232610+00:00', 11125, null, ''),
(9, 'overture_places', '2026-06-17.0', '2026-07-15 01:13:06.074715+00:00', 41558, null, ''),
(10, 'walkability', 'chicago_pois_800m', '2026-07-15 01:13:59.468497+00:00', 308, null, '')
on conflict (source, vintage_label) do update set id = excluded.id, retrieved_at = excluded.retrieved_at, row_count = excluded.row_count, checksum = excluded.checksum, notes = excluded.notes;
select setval('dataset_versions_id_seq', (select coalesce(max(id), 1) from dataset_versions));
