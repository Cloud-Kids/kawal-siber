# ==============================================================================
# Hardened Tools Agent Container Image for KAWAL SIBER (ks-tools-01)
# Includes Nmap, Suricata CLI, and Python microservice execution agent
# ==============================================================================
FROM python:3.12-slim AS runtime

# Install system dependencies & security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        nmap \
        suricata \
        libpcap-dev \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated unprivileged user
RUN groupadd --gid 1002 toolsuser && \
    useradd --uid 1002 --gid 1002 --no-create-home --shell /sbin/nologin toolsuser

WORKDIR /app

# Install Python requirements for tools agent
RUN pip install --no-cache-dir \
    fastapi==0.115.5 \
    uvicorn[standard]==0.32.1 \
    pydantic==2.10.2

# Copy agent application code
COPY agent /app/agent

RUN chown -R toolsuser:toolsuser /app

USER toolsuser

ENV PYTHONUNBUFFERED=1
ENV PORT=9000

EXPOSE 9000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -s -f http://127.0.0.1:9000/health || exit 1

CMD ["uvicorn", "agent.tools_agent:app", "--host", "0.0.0.0", "--port", "9000"]

