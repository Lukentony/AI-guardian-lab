FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent/main.py .
RUN mkdir -p config
CMD ["python", "main.py"]
