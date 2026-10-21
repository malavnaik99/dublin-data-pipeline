-- Latest known details per station (station info is saved once a day).
select
    station_id,
    json_extract_string(name, '$[0].text')             as station_name,
    lat,
    lon,
    capacity,
    address
from read_parquet('{{ var("raw_path") }}/stations/*/*.parquet', hive_partitioning = false, union_by_name = true)
qualify row_number() over (partition by station_id order by fetched_at desc) = 1
