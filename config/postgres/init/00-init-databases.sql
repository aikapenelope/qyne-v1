-- QYNE v1 — PostgreSQL Init (runs once on first start)
-- Two separate databases. Each service is full owner of its database.

CREATE USER directus_user WITH PASSWORD 'directus_password';
CREATE USER prefect_user WITH PASSWORD 'prefect_password';

CREATE DATABASE directus_db OWNER directus_user;
CREATE DATABASE prefect_db OWNER prefect_user;

-- Extensions (must be created by superuser in each database)
\c directus_db
CREATE EXTENSION IF NOT EXISTS vector;

\c prefect_db
CREATE EXTENSION IF NOT EXISTS pg_trgm;
