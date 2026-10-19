FROM python:3.11-slim
RUN groupadd --gid 1000 guardian && \
    useradd --uid 1000 --gid guardian --no-create-home guardian
WORKDIR /app
COPY guardian/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY guardian/ /app/guardian/
COPY database/ /app/database/
# Runtime data is outside Python's import tree and outside application code.
RUN mkdir -p /var/lib/guardian /var/lib/guardian-learned && \
    chown guardian:guardian /var/lib/guardian /var/lib/guardian-learned && \
    chmod +x /app/guardian/entrypoint.sh
USER guardian
ENV DB_PATH=/var/lib/guardian/audit.db
ENV LEARNED_PATH=/var/lib/guardian-learned/learned_patterns.yaml
EXPOSE 5000
ENTRYPOINT ["/app/guardian/entrypoint.sh"]
