-- dataset_versions: 9 rows (generated; idempotent)
insert into dataset_versions (id, source, vintage_label, retrieved_at, row_count, checksum, notes) values
(1, 'geo_spine', 'chicago_tiger_blocks2020', '2026-07-15 01:17:25.589172+00:00', 1408, null, ''),
(2, 'crosswalk', 'chicago_2020_blocks_p1', '2026-07-15 01:17:35.438034+00:00', 802, null, ''),
(3, 'socrata_crime', 'chicago_2023-07-16_w3y', '2026-07-15 01:17:36.009479+00:00', 744359, null, ''),
(4, 'zillow', 'zip_202607_hudzcta520_rel_area', '2026-07-15 01:19:49.048579+00:00', 1602, null, ''),
(5, 'cdc_places', 'tract_gis_yjkw-uj5s', '2026-07-15 01:19:58.445410+00:00', 3984, null, ''),
(6, 'nfhl', 'chicago_sfha', '2026-07-15 01:19:59.781453+00:00', 77, null, ''),
(7, 'urban_edu', 'ccd2022_edfacts2020', '2026-07-15 01:20:19.519965+00:00', 1415, null, ''),
(8, 'gtfs', 'chicago_static', '2026-07-15 01:20:20.009351+00:00', 11125, null, ''),
(9, 'overture_places', '2026-06-17.0', '2026-07-15 01:20:33.983775+00:00', null, null, '')
on conflict (source, vintage_label) do update set id = excluded.id, retrieved_at = excluded.retrieved_at, row_count = excluded.row_count, checksum = excluded.checksum, notes = excluded.notes;
select setval('dataset_versions_id_seq', (select coalesce(max(id), 1) from dataset_versions));
