-- dataset_versions: 10 rows (generated; idempotent)
insert into dataset_versions (id, source, vintage_label, retrieved_at, row_count, checksum, notes) values
(1, 'geo_spine', 'chicago_tiger_blocks2020', '2026-07-15 01:24:59.635694+00:00', 1408, null, ''),
(2, 'crosswalk', 'chicago_2020_blocks_p1', '2026-07-15 01:25:06.087025+00:00', 802, null, ''),
(3, 'socrata_crime', 'chicago_2023-07-16_w3y', '2026-07-15 01:25:06.716996+00:00', 744359, null, ''),
(4, 'zillow', 'zip_202607_hudzcta520_rel_area', '2026-07-15 01:26:59.046944+00:00', 1602, null, ''),
(5, 'cdc_places', 'tract_gis_yjkw-uj5s', '2026-07-15 01:27:07.937639+00:00', 3984, null, ''),
(6, 'nfhl', 'chicago_sfha', '2026-07-15 01:27:09.437992+00:00', 77, null, ''),
(7, 'urban_edu', 'ccd2022_edfacts2020', '2026-07-15 01:27:41.470769+00:00', 1415, null, ''),
(8, 'gtfs', 'chicago_static', '2026-07-15 01:27:41.885335+00:00', 11125, null, ''),
(9, 'overture_places', '2026-06-17.0', '2026-07-15 01:27:53.535468+00:00', 41558, null, ''),
(10, 'walkability', 'chicago_pois_800m', '2026-07-15 01:28:13.098175+00:00', 308, null, '')
on conflict (source, vintage_label) do update set id = excluded.id, retrieved_at = excluded.retrieved_at, row_count = excluded.row_count, checksum = excluded.checksum, notes = excluded.notes;
select setval('dataset_versions_id_seq', (select coalesce(max(id), 1) from dataset_versions));
