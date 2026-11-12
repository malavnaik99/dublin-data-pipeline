-- Leaves out placeholder stations (e.g. "STATION118") and stations with no docks.
select station_id, station_name, address, lat, lon, capacity
from {{ ref('stg_stations') }}
where capacity > 0 and station_name not like 'STATION%'
