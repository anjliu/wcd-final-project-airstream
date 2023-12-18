-- query the most recent data
select
    from_unixtime(updated) as time_updated, -- convert epoch time to readable time
    lat,									-- latitude
    lng,									-- longitude
	dir,									-- direction
    flight_iata								-- IATA flight code
from air_stream
order by time_updated desc
limit 100;

-- query the last departed flight
with ordered as (
	select flight_iata, from_unixtime(min(updated)) as earliest
	from air_stream
	group by flight_iata
)
select flight_iata
from ordered
order by earliest desc
limit 1;

-- get the records with latest timestamp for each flight
select 
	from_unixtime(updated) as time_updated,
	lat,
	lng,
	dir,
	flight_iata 
from air_stream a1 
where (a1.flight_iata,a1.updated) in (
	select a.flight_iata, 
	max(updated) 
	from air_stream a 
	group by a.flight_iata
);

-- get records where the timestamp matches the latest timestamp in the table
select 
	from_unixtime(updated) as time_updated,
	lat,
	lng,
	dir,
	flight_iata 
from air_stream
where updated in (
    select max(updated) from air_stream
    );