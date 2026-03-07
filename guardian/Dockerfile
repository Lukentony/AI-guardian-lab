FROM python:3.11-slim

# Create unprivileged user
RUN groupadd -r guardian && useradd -r -g guardian guardian

WORKDIR /app

# Install sqlite3 for db initialization
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY guardian/main.py .
COPY guardian/intent.py .
COPY guardian/schema.sql .
COPY guardian/entrypoint.sh .
COPY config/ config/

RUN chmod +x /app/entrypoint.sh && \
    chown -R guardian:guardian /app

USER guardian

EXPOSE 5000

# Entrypoint for automatic DB initialization (SEC-04)
ENTRYPOINT ["/app/entrypoint.sh"]
