-- One row per hourly Met Éireann observation (Dublin Airport). Each hourly file repeats the day so far,
-- so keep the latest copy of each observation. Times are Irish local time; converted to UTC here.
with obs as (
    select
        timezone('Europe/Dublin',
                 try_strptime(date, ['%d-%m-%Y', '%Y-%m-%d'])::date + cast(reportTime || ':00' as time)) as observed_at,
        try_cast(temperature as double)                as temperature_c,
        try_cast(rainfall as double)                   as rainfall_mm,
        try_cast(windSpeed as double)                  as wind_kmh,
        try_cast(humidity as double)                   as humidity_pct,
        weatherDescription                             as weather_description,
        fetched_at
    from read_parquet('{{ var("raw_path") }}/weather/*/*.parquet', hive_partitioning = false, union_by_name = true)
)
select * exclude (fetched_at)
from obs
where observed_at is not null
qualify row_number() over (partition by observed_at order by fetched_at desc) = 1
