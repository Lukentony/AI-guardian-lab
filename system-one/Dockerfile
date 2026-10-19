FROM python:3.13-slim
WORKDIR /app
# A quarantined dependency set must not produce a runnable image.
COPY qualification.py .
RUN python qualification.py
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY serve.py .
RUN groupadd --gid 1000 model && \
    useradd --uid 1000 --gid model --no-create-home model && \
    mkdir /models && chown model:model /models
USER model
ENV HF_HOME=/models
ENV HF_HUB_DISABLE_IMPLICIT_TOKEN=1
ENV HF_HUB_DISABLE_TELEMETRY=1
EXPOSE 8009
CMD ["python", "serve.py", "--host", "0.0.0.0", "--port", "8009"]
