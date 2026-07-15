-- dataset_versions: 11 rows (generated; idempotent)
insert into dataset_versions (id, source, vintage_label, retrieved_at, row_count, checksum, notes) values
(1, 'geo_spine', 'chicago_tiger_blocks2020', '2026-07-15 01:31:13.738422+00:00', 1408, null, ''),
(2, 'crosswalk', 'chicago_2020_blocks_p1', '2026-07-15 01:31:20.956972+00:00', 802, null, ''),
(3, 'socrata_crime', 'chicago_2023-07-16_w3y', '2026-07-15 01:31:21.537674+00:00', 744359, null, ''),
(4, 'zillow', 'zip_202607_hudzcta520_rel_area', '2026-07-15 01:33:10.314339+00:00', 1602, null, ''),
(5, 'fema_nri', 'tracts_arcgis_service', '2026-07-15 01:33:17.518873+00:00', 5324, null, ''),
(6, 'cdc_places', 'tract_gis_yjkw-uj5s', '2026-07-15 01:33:18.550806+00:00', 3984, null, ''),
(7, 'nfhl', 'chicago_sfha', '2026-07-15 01:33:20.501838+00:00', 77, null, ''),
(8, 'urban_edu', 'ccd2022_edfacts2020', '2026-07-15 01:33:38.970071+00:00', 1415, null, ''),
(9, 'gtfs', 'chicago_static', '2026-07-15 01:33:39.508108+00:00', 11125, null, ''),
(10, 'overture_places', '2026-06-17.0', '2026-07-15 01:33:54.606759+00:00', 41558, null, ''),
(11, 'walkability', 'chicago_pois_800m', '2026-07-15 01:34:46.727464+00:00', 308, null, '')
on conflict (source, vintage_label) do update set id = excluded.id, retrieved_at = excluded.retrieved_at, row_count = excluded.row_count, checksum = excluded.checksum, notes = excluded.notes;
select setval('dataset_versions_id_seq', (select coalesce(max(id), 1) from dataset_versions));
