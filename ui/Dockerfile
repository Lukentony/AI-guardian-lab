FROM python:3.11-slim

# Create unprivileged user
RUN groupadd -r ui && useradd -r -g ui ui

WORKDIR /app

# Ensure database directory exists if mounted locally
RUN mkdir -p /app/database && chown -R ui:ui /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/

RUN chown -R ui:ui /app

USER ui

EXPOSE 8080

CMD ["python", "app.py"]
