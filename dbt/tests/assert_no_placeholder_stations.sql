-- Every station must have docks and a real name (not a placeholder like "STATION118").
select * from {{ ref('dim_station') }} where capacity = 0 or station_name like 'STATION%'
