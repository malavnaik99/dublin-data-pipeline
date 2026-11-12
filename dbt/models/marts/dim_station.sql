-- Leaves out placeholder stations (e.g. "STATION118").
select station_id, station_name, address, lat, lon, capacity
from {{ ref('stg_stations') }}
where station_name not like 'STATION%'
