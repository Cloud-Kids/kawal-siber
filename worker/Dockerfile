FROM python:3.12-slim AS runtime

# Install Nmap securely without recommended packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends nmap && \
    rm -rf /var/lib/apt/lists/*

# Verify Nmap installation during build
RUN nmap --version

# Run worker as unprivileged user
RUN groupadd --gid 1001 worker && \
    useradd --uid 1001 --gid 1001 --no-create-home --shell /sbin/nologin worker

WORKDIR /app

COPY worker/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app (for shared models) and worker code
COPY backend/app ./app
COPY worker ./worker

# Set ownership
RUN chown -R worker:worker /app

USER worker

ENV PYTHONUNBUFFERED=1
ENV SCAN_ENABLED=false
ENV DATABASE_URL=sqlite:////data/kawal_siber.db

CMD ["python", "-m", "worker.main"]

