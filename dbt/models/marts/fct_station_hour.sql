{{ config(materialized='incremental', unique_key=['station_id', 'hour_utc'], incremental_strategy='delete+insert') }}
-- Fact table: one row per station per hour. Incremental and idempotent: each run recomputes the last 3 hours.
select *
from {{ ref('int_bikes_hourly') }}
{% if is_incremental() %}
where hour_utc >= (select max(hour_utc) - interval 3 hour from {{ this }})
{% endif %}
