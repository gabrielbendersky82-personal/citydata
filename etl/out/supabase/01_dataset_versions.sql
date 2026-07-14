-- dataset_versions: 9 rows (generated; idempotent)
insert into dataset_versions (id, source, vintage_label, retrieved_at, row_count, checksum, notes) values
(1, 'geo_spine', 'chicago_tiger_blocks2020', '2026-07-14 23:49:53.991705+00:00', 1408, null, ''),
(2, 'crosswalk', 'chicago_2020_blocks_p1', '2026-07-14 23:50:01.875940+00:00', 802, null, ''),
(3, 'socrata_crime', 'chicago_2023-07-15_w3y', '2026-07-14 23:50:02.491233+00:00', null, null, ''),
(4, 'cdc_places', 'tract_gis_yjkw-uj5s', '2026-07-14 23:55:39.375100+00:00', 3984, null, ''),
(5, 'nfhl', 'chicago_sfha', '2026-07-14 23:55:40.682553+00:00', 77, null, ''),
(6, 'urban_edu', 'ccd2022_edfacts2020', '2026-07-14 23:56:02.901866+00:00', 1415, null, ''),
(7, 'gtfs', 'chicago_static', '2026-07-14 23:56:03.454767+00:00', 11125, null, ''),
(8, 'overture_places', '2026-06-17.0', '2026-07-14 23:56:18.552705+00:00', 41558, null, ''),
(9, 'walkability', 'chicago_pois_800m', '2026-07-14 23:57:10.166520+00:00', 308, null, '')
on conflict (source, vintage_label) do update set id = excluded.id, retrieved_at = excluded.retrieved_at, row_count = excluded.row_count, checksum = excluded.checksum, notes = excluded.notes;
select setval('dataset_versions_id_seq', (select coalesce(max(id), 1) from dataset_versions));
