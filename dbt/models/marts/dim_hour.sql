-- One row per UTC hour covered by the bike data, with Dublin local time and that hour's weather.
with hours as (
    select unnest(generate_series(min(hour_utc), max(hour_utc), interval 1 hour)) as hour_utc
    from {{ ref('int_bikes_hourly') }}
)
select
    h.hour_utc,
    timezone('Europe/Dublin', h.hour_utc)              as hour_local,
    cast(timezone('Europe/Dublin', h.hour_utc) as date) as local_date,
    hour(timezone('Europe/Dublin', h.hour_utc))        as local_hour,
    dayname(timezone('Europe/Dublin', h.hour_utc))     as weekday,
    isodow(timezone('Europe/Dublin', h.hour_utc)) >= 6 as is_weekend,
    w.temperature_c,
    w.rainfall_mm,
    w.wind_kmh,
    w.humidity_pct,
    w.weather_description
from hours h
left join {{ ref('stg_weather') }} w on w.observed_at = h.hour_utc
