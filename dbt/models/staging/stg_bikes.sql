-- One row per station per snapshot (about every 15 minutes).
select distinct
    station_id,
    cast(fetched_at as timestamptz)                    as fetched_at,
    num_vehicles_available                             as bikes,
    num_docks_available                                as docks,
    coalesce(num_vehicles_disabled, 0)                 as bikes_disabled,
    coalesce(num_docks_disabled, 0)                    as docks_disabled,
    is_installed,
    is_renting,
    is_returning,
    try_cast(last_reported as timestamptz)             as last_reported
from read_parquet('{{ var("raw_path") }}/bikes/*/*.parquet', hive_partitioning = false, union_by_name = true)
where station_id is not null
