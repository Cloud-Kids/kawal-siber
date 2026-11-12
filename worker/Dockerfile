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

# Deep Eye CLI runtime dependencies (curated subset of tools/deep-eye/
# requirements.txt — heavy optional SDKs like selenium/playwright/AI
# providers are intentionally excluded; the adapter falls back to its
# built-in deterministic engine when the CLI cannot run).
RUN pip install --no-cache-dir \
        rich==15.0.0 \
        jinja2==3.1.6 \
        requests==2.34.2 \
        beautifulsoup4==4.15.0 \
        lxml==6.1.3 \
        dnspython==2.9.2 \
        python-whois==0.9.6

# Copy backend app (for shared models), worker code, and Deep Eye submodule
COPY backend/app ./app
COPY worker ./worker
COPY tools/deep-eye ./tools/deep-eye

# Set ownership
RUN chown -R worker:worker /app

USER worker

ENV PYTHONUNBUFFERED=1
ENV SCAN_ENABLED=false
ENV DATABASE_URL=sqlite:////data/kawal_siber.db
ENV KAWAL_STORAGE_ROOT=/data
ENV DEEP_EYE_ROOT=/app/tools/deep-eye

CMD ["python", "-m", "worker.main"]

