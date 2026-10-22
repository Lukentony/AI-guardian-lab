FROM python:3.13-slim
WORKDIR /app

# The pinned Kev metadata still caps torch at <2.9. Install the reviewed torch
# first, then the hashed dependency set, then Kev without dependency
# resolution so the cap cannot silently replace the qualified runtime.
COPY requirements.lock .
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        'torch==2.13.0+cpu' \
    && pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir --no-deps \
        'kev @ https://github.com/jaredpalmer/kev/archive/1f04cfa28e6a708485b28a9585010b9e436b776e.tar.gz#sha256=3d0230dbc5c6155cf6a0933696998a9ad6942754a2af1a95c88bf23e1d2cc631'

COPY qualification.py .
# Verify the runtime after installation, not before: the gate must inspect what
# would actually serve inference.
RUN python qualification.py
COPY serve.py .
RUN groupadd --gid 1000 model && \
    useradd --uid 1000 --gid model --no-create-home model && \
    mkdir /models && chown model:model /models
USER model
ENV HF_HOME=/models
ENV HF_HUB_DISABLE_IMPLICIT_TOKEN=1
ENV HF_HUB_DISABLE_TELEMETRY=1
ENV SYSTEM_ONE_THREADS=8
ENV KEV_PREFIX_CACHE=4
EXPOSE 8009
CMD ["python", "serve.py", "--host", "0.0.0.0", "--port", "8009"]
