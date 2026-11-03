# Run the project

Make sure Docker Compose is installed, then start the containers:

```sh
docker compose up --build -d
```

On the first run, prepare the database:

```sh
docker compose exec db psql -U user -d med_expert -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
docker compose exec api alembic upgrade head
```

To import data from the reference document, run:

```sh
docker compose exec api python parser/parse_docx.py
```

The API is available at <http://localhost:8000>; its documentation is at <http://localhost:8000/docs>.

Stop the containers with `docker compose down`.
