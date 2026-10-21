select station_id, station_name, address, lat, lon, capacity
from {{ ref('stg_stations') }}
