# ======== promotions-master/Dockerfile ========
FROM python:3.11-slim

WORKDIR /app

# Preinstall deps for building psycopg from source and general compatibility
# (currently using psycopg[binary]; can be trimmed later if appropriate)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy lockfiles first to leverage image layer caching
COPY Pipfile Pipfile.lock /app/
RUN pip install -U pip pipenv && pipenv install --system --deploy

# Copy application code
COPY service /app/service
COPY wsgi.py ./

# Default fallback to SQLite (for local/dev convenience only; K8s will override via Deployment env)
ENV DATABASE_URI=sqlite:////tmp/promotions.db

# Expose application port
EXPOSE 8080

# Start the Flask app with Gunicorn (wsgi:app)
CMD ["gunicorn","--bind","0.0.0.0:8080","--log-level=info","wsgi:app"]
