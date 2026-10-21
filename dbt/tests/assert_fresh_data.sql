-- Freshness: the newest snapshot must be under 2 hours old.
select max(fetched_at) as newest from {{ ref('stg_bikes') }}
having max(fetched_at) < now() - interval 2 hour
