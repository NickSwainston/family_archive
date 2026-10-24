# family_archive
Django website with two main purposes: 1) To be a blog to post updates that the entire family can see. 2) To archive the family history


## Install

Install apt dependencies

```
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib libpq-dev python3-dev graphviz python3-pip
```

Install python dependencies

```
uv sync
```


Set up the `.env` file

```
SECRET_KEY=your-django-secret-key-here
DEBUG=True
PGDATABASE=family_archive
PGUSER=dbuser
PGPASSWORD=dbpassword
ALLOWED_HOSTS=127.0.0.1,localhost
PGHOST=localhost
```

You can generate a SECRET_KEY at https://miniwebtool.com/django-secret-key-generator/

Set up the database

```
sudo -u postgres psql
```

Then in the PostgreSQL prompt:

```
CREATE DATABASE family_archive;
CREATE USER dbuser WITH ENCRYPTED PASSWORD 'dbpassword';
ALTER ROLE dbuser SET client_encoding TO 'utf8';
ALTER ROLE dbuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE dbuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE family_archive TO dbuser;
GRANT ALL ON SCHEMA public TO dbuser;
\q
```

## Migrations

```
uv run python manage.py migrate
```

Superuser
```
uv run python manage.py createsuperuser
```

## Run the server

```
uv run python manage.py runserver
```

## Docker

Bump the version, commit, tag, build and push to the registry:
```
make release REGISTRY=host:port BUMP=patch  # or minor/major
```
`make push` builds and pushes the current version without bumping.

## Event timeline

Family events (title, place, date range, photos) are shown at `/timeline/`. Any logged-in user can add photos to an event; only its creator or a superuser can edit it.
