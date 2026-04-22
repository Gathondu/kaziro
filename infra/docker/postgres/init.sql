-- Bootstrap script run automatically by the official `postgres` image on
-- first boot (it sources every file mounted under
-- ``/docker-entrypoint-initdb.d`` against the default database).
--
-- Phase 0 only needs the ``pgvector`` extension; later migrations
-- (T1.x) introduce the application schema via Alembic.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
