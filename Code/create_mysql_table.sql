-- this query creates the mysql table used to receive data from Nifi
create table air_stream(
	record_id int not null auto_increment,	-- auto-generate a record_id
	updated int, 							-- time of record in epoch time
	hex varchar(10),						-- hex code for flight
	flag varchar(10),						-- country flag
	lat real not null,						-- latitude
	lng real not null,						-- longitude
	alt real,								-- altitude
	dir real,								-- direction
	speed real,								-- speed
	flight_iata varchar(10),				-- IATA code for flight
	arr_iata varchar(10),					-- IATA code for the arrival airport of the flight
	airline_iata varchar(10),				-- IATA code for the airline
	aircraft_icao varchar(10),				-- ICAO code for the aircraft
	primary key (record_id)					-- use the record_id as primary key
);