FROM python:3.11-slim
WORKDIR /app
COPY executor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY executor/app.py .
COPY guardian/guardian/execution_token.py .
RUN groupadd --gid 1000 executor && \
    useradd --uid 1000 --gid executor --no-create-home executor && \
    mkdir -p /workspace /tmp/executor && \
    chown executor:executor /workspace /tmp/executor
ENV PYTHONDONTWRITEBYTECODE=1
USER executor
EXPOSE 5002
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "1", "--timeout", "15", "app:app"]
