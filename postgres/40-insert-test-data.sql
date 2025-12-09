\c tickets 

\c flights

truncate airport cascade;
truncate flight cascade;
insert into airport(name,city,country) values ('Шереметьево', 'Москва', 'Россия'),('Пулково', 'Санкт-Петербург', 'Россия');

insert into flight(flight_number,datetime,from_airport_id,to_airport_id,price) values (
    'AFL031',
    '2021-10-08 20:00',
    (select id from airport where name = 'Пулково'),
    (select id from airport where name = 'Шереметьево'),
    1500
);

\c privileges

truncate privilege cascade;
insert into privilege(username, balance) values 
    ('user', 0);