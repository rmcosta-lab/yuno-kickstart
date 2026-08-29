# Run local infrastructure

The bootstrap runs PostgreSQL locally and keeps the application processes on the host. It does not add Redis, queues, or deployment infrastructure before a challenge requires them.

## Start PostgreSQL

Copy the local environment template, then start the database:

```bash
cp .env.example .env
make postgres-up
```

Docker Compose publishes PostgreSQL on `localhost:5432` and stores data in the `postgres_data` volume. The template credentials are for local development only.

## Check container health

Inspect the service after startup:

```bash
docker compose ps
```

The health check uses `pg_isready`. Application startup and migrations should wait for the container to report `healthy`.

## Stop PostgreSQL

Stop the container without deleting its data:

```bash
make postgres-down
```

Deleting the named volume removes local database data and requires an explicit operator action.
