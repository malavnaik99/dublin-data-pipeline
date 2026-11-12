-- No placeholder stations like "STATION118". (Capacity 0 is allowed: Parnell Square North reports 0 but is real.)
select * from {{ ref('dim_station') }} where station_name like 'STATION%'
