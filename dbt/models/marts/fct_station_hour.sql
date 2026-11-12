{{ config(materialized='incremental', unique_key=['station_id', 'hour_utc'], incremental_strategy='delete+insert',
          post_hook="delete from {{ this }} where station_id not in (select station_id from {{ ref('dim_station') }})") }}
-- Fact table: one row per station per hour. Incremental and idempotent: each run recomputes the last 3 hours.
-- Only stations in dim_station; the post-hook also drops older rows of stations that left it (e.g. STATION118).
select *
from {{ ref('int_bikes_hourly') }}
where station_id in (select station_id from {{ ref('dim_station') }})
{% if is_incremental() %}
  and hour_utc >= (select max(hour_utc) - interval 3 hour from {{ this }})
{% endif %}
