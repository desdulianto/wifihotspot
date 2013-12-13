alter table radcheck add column time timestamp;
alter table radcheck add column contact_id integer;

create table contact (
    id serial primary key not null,
    name varchar(64) not null default '',
    phone varchar(20) not null default ''
);

create index contact_name on contact using btree (name);
create index contact_phone on contact using btree (phone);
