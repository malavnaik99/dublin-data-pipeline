-- Bike and dock counts can't be negative.
select * from {{ ref('stg_bikes') }} where bikes < 0 or docks < 0
