FROM python:3.11-slim
RUN groupadd -r guardian && useradd -r -g guardian guardian
WORKDIR /app
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /app/database /app/config && \
    chown -R guardian:guardian /app
COPY guardian/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY guardian/guardian/main.py .
COPY guardian/guardian/intent.py .
COPY guardian/schema.sql .
COPY guardian/entrypoint.sh .
COPY guardian/config/ config/
COPY tests/ tests/
RUN chmod +x /app/entrypoint.sh && \
    chown -R guardian:guardian /app
USER guardian
EXPOSE 5000
ENTRYPOINT ["/app/entrypoint.sh"]
