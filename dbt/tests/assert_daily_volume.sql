-- Volume: at least 72 of the expected ~96 snapshots in the last 24 hours (75%).
select count(distinct fetched_at) as runs from {{ ref('stg_bikes') }}
where fetched_at >= now() - interval 24 hour
having count(distinct fetched_at) < 72
