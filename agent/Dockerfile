FROM python:3.11-slim
RUN groupadd --gid 1000 agent && \
    useradd --uid 1000 --gid agent --no-create-home agent
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent/main.py .
RUN mkdir -p /workspace && chown agent:agent /workspace
USER agent
EXPOSE 5001
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "60", "main:app"]
