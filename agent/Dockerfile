FROM python:3.11-slim

# Create unprivileged user
RUN groupadd -r agent && useradd -r -g agent agent

WORKDIR /app

# Ensure directories exist and have correct permissions
RUN mkdir -p /app/config && \
    chown -R agent:agent /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/main.py .

RUN chown -R agent:agent /app

USER agent

EXPOSE 5001

# Run with Gunicorn (SEC-04)
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "60", "main:app"]
