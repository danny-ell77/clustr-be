# Staging Dockerfile for ClustR Backend
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings_production

# Create non-root user with group
RUN addgroup --system appuser && adduser --system --no-create-home --ingroup appuser appuser

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/base.txt requirements/base.txt
COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements/production.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Create directories, collect static files, and set permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media \
    && python manage.py collectstatic --noinput --clear \
    && chown -R appuser:appuser /app/logs /app/staticfiles /app/media

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "config.wsgi:application"]