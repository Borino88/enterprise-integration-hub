# ==============================================================================
# Stage 1: Build & Dependency Packaging
# ==============================================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build wheels for production dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ==============================================================================
# Stage 2: Production Runtime
# ==============================================================================
FROM python:3.11-slim-bookworm AS runtime

# OCI Standard Metadata Labels
LABEL org.opencontainers.image.title="Enterprise Integration Hub"
LABEL org.opencontainers.image.description="B2B integration engine with webhook ingestion, retry policies, dead-letter queue (DLQ) recovery, and synthetic CRM/ERP mock endpoints."
LABEL org.opencontainers.image.source="https://github.com/Borino88/enterprise-integration-hub"
LABEL org.opencontainers.image.url="https://fattahi.xyz"
LABEL org.opencontainers.image.documentation="https://github.com/Borino88/enterprise-integration-hub#readme"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.authors="Mahdi Fattahi <a.borino88@gmail.com>"

# Create unprivileged non-root runtime user and group
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install precompiled wheels from builder stage
COPY --from=builder /build/wheels /tmp/wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels -r requirements.txt \
    && rm -rf /tmp/wheels

# Copy source application
COPY src/ ./src/

# Set ownership to unprivileged user
RUN chown -R appuser:appgroup /app

# Switch to non-root runtime user
USER appuser

# Health check endpoint verification using urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

EXPOSE 8000

# Execute server as non-root user
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
