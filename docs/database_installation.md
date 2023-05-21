# Database Installation

## Dependancies

For Ubuntu or Debian Linux:

```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib libpq-dev python3-dev graphviz python3-pip gosu postgresql-q3c locales
```

Then install the python requirements (recommended in its own virtual environment) using:

```bash
cd family_archive
poetry install
```

## Webapp settings

Use [python-decouple](https://pypi.org/project/python-decouple/) to put the webapp settings and secrets into a file in `family_archive/.env`:

```python
SECRET_KEY=[django-secret](https://miniwebtool.com/django-secret-key-generator/)
DEBUG=True
DB_NAME=family_archive
DB_USER=dbuser
DB_PASSWORD=dbpassword
ALLOWED_HOSTS=127.0.0.1
DB_HOST=localhost
```

## Start the Postgres Database

The following commands will set up the Postgres database for the web app. Replace $DB_USER and $DB_PASSWORD with the environment variable values.

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';

ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';
```



## Setup database for the first time

Run the following commands from the gleam_webapp subdirectory so Django can setup up the database structure and upload defaults

```bash
python manage.py makemigrations archive_app
python manage.py migrate archive_app
python manage.py migrate
python manage.py migrate --run-syncdb
```

## Create a superuser

These commands will set up a superuser account.

```bash
python manage.py createsuperuser
```


## Delete Postgres Database

Only do this is you want to restart the database!

To delete the database use the following commands

```sql
sudo -u postgres psql

DROP DATABASE $DB_NAME;
CREATE DATABASE $DB_NAME;
```

You will then have to recreate the database using the commands in [Setup database for the first time](database_installation.md#Setup database for the first time)