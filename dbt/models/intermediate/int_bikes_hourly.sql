-- Station x UTC hour summary of the 15-minute snapshots.
select
    station_id,
    date_trunc('hour', fetched_at)                     as hour_utc,
    count(*)                                           as snapshots,
    avg(bikes)                                         as avg_bikes,
    min(bikes)                                         as min_bikes,
    max(bikes)                                         as max_bikes,
    avg(docks)                                         as avg_free_docks,
    avg(case when bikes = 0 then 1 else 0 end)         as share_empty,
    avg(case when docks = 0 then 1 else 0 end)         as share_full,
    avg(case when is_renting then 1 else 0 end)        as share_renting
from {{ ref('stg_bikes') }}
group by all
