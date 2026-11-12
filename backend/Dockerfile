# ---------------------------------------------------------------------------
# Stage 1: builder — install Python dependencies into /install
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools (needed for some C-extension packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------------------------------------------------------------------------
# Stage 2: runtime — lean production image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Suricata is required for offline PCAP analysis (monitoring routes run it
# as a background task inside this container). Pinned via distro package.
RUN apt-get update && apt-get install -y --no-install-recommends \
        suricata \
    && rm -rf /var/lib/apt/lists/* \
    && suricata --build-info | head -5

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KAWAL_STORAGE_ROOT=/data

# Create a non-root user
RUN groupadd --gid 1001 appuser \
 && useradd --uid 1001 --gid 1001 --no-create-home --shell /sbin/nologin appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application source
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create /data directory for SQLite persistence and set ownership
RUN mkdir -p /data && chown appuser:appuser /data

# Switch to non-root user
USER appuser

EXPOSE 8000

# Healthcheck — curl must be available on the slim image; install it via builder
# stage or use wget as fallback
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" \
    || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
