select station_id, hour_utc from {{ ref('fct_station_hour') }} group by all having count(*) > 1
