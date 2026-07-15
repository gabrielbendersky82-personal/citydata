-- dataset_versions: 12 rows (generated; idempotent)
insert into dataset_versions (id, source, vintage_label, retrieved_at, row_count, checksum, notes) values
(1, 'geo_spine', 'chicago_tiger_blocks2020', '2026-07-15 08:43:20.981285+00:00', 1408, null, ''),
(2, 'crosswalk', 'chicago_2020_blocks_p1', '2026-07-15 08:47:50.907855+00:00', 802, null, ''),
(3, 'socrata_crime', 'chicago_2023-07-16_w3y', '2026-07-15 08:47:51.534290+00:00', 744359, null, ''),
(4, 'zillow', 'zip_202607_hudzcta520_rel_area', '2026-07-15 08:49:42.773159+00:00', 1602, null, ''),
(5, 'fema_nri', 'tracts_arcgis_service', '2026-07-15 08:49:49.999153+00:00', 5324, null, ''),
(6, 'cdc_places', 'tract_gis_yjkw-uj5s', '2026-07-15 08:49:51.122313+00:00', 3984, null, ''),
(7, 'nfhl', 'chicago_sfha', '2026-07-15 08:49:53.686500+00:00', 77, null, ''),
(8, 'urban_edu', 'ccd2022_edfacts2020', '2026-07-15 08:50:12.497924+00:00', 1415, null, ''),
(9, 'gtfs', 'chicago_static', '2026-07-15 08:50:13.044861+00:00', 11125, null, ''),
(10, 'overture_places', '2026-06-17.0', '2026-07-15 08:50:27.984085+00:00', 41558, null, ''),
(11, 'walkability', 'chicago_pois_800m', '2026-07-15 08:51:04.798508+00:00', 308, null, ''),
(12, 'acs', 'acs5_2023', '2026-07-15 08:51:11.011020+00:00', 10549, null, '')
on conflict (source, vintage_label) do update set id = excluded.id, retrieved_at = excluded.retrieved_at, row_count = excluded.row_count, checksum = excluded.checksum, notes = excluded.notes;
select setval('dataset_versions_id_seq', (select coalesce(max(id), 1) from dataset_versions));
