FROM python:3.11-slim

# Create unprivileged user
RUN groupadd -r guardian && useradd -r -g guardian guardian

WORKDIR /app

# Ensure directories exist and have correct permissions
RUN mkdir -p /app/database /app/config && \
    chown -R guardian:guardian /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY guardian/main.py .
COPY config/ config/

RUN chown -R guardian:guardian /app

USER guardian

EXPOSE 5000

# Run with Gunicorn (SEC-04)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "main:app"]
