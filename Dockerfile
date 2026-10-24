FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_HASHED=True

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN uv sync --frozen --no-dev
# Placeholder values so settings.py can load; .env is excluded by .dockerignore and real values come at runtime
RUN SECRET_KEY=build DEBUG=False ALLOWED_HOSTS=localhost PGDATABASE=x PGUSER=x PGPASSWORD=x PGHOST=x \
    uv run python manage.py collectstatic --noinput

EXPOSE 8000

# Exec form so signals are delivered properly. `sh -c` is kept only to expand the GUNICORN_* defaults;
# `exec` then replaces the shell so gunicorn runs as PID 1 and receives SIGTERM for a graceful shutdown.
# The venv binary is called directly (not `uv run`) so no extra process sits in between.
CMD ["sh", "-c", "exec /app/.venv/bin/gunicorn family_archive.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-300}"]
