# ==============================================================================
# Golf Data Analysis Application - Docker Image
# ==============================================================================
# This Dockerfile creates an optimized container for the Streamlit-based
# golf data analysis application. It uses multi-stage builds and layer caching
# to minimize image size and speed up builds.
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Base Python Image with System Dependencies
# ------------------------------------------------------------------------------
# We use Python 3.11 slim (Debian-based) for smaller image size
FROM python:3.11-slim as base

# Set environment variables
# PYTHONUNBUFFERED: Ensures Python output is sent directly to terminal (no buffering)
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disk
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies needed for Python packages
# - build-essential: Compiler tools for packages with C extensions
# - curl: For health checks
# - postgresql-client: For psycopg2 (Supabase connection)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# Stage 2: Python Dependencies Installation
# ------------------------------------------------------------------------------
# This stage installs Python dependencies. By copying requirements first,
# we leverage Docker's layer caching - if requirements don't change, this
# layer is reused on subsequent builds.
FROM base as dependencies

# Copy requirements files
COPY requirements.txt requirements_cloud.txt ./

# Install Python dependencies
# We install both requirements.txt and requirements_cloud.txt
# Using --no-cache-dir reduces image size by not storing pip cache
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_cloud.txt

# ------------------------------------------------------------------------------
# Stage 3: Final Application Image
# ------------------------------------------------------------------------------
FROM base as final

# Copy installed packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Create non-root user for security
# Running as non-root is a Docker best practice
RUN useradd -m -u 1000 golfuser && \
    chown -R golfuser:golfuser /app

# Create directories for persistent data
# These will be mounted as volumes to persist data between container restarts
RUN mkdir -p /app/data /app/media /app/logs && \
    chown -R golfuser:golfuser /app/data /app/media /app/logs

# Copy application code
# We do this late in the Dockerfile so code changes don't invalidate
# the dependency layers above
COPY --chown=golfuser:golfuser . .

# Switch to non-root user
USER golfuser

# Expose Streamlit's default port
# Streamlit runs on port 8501 by default
EXPOSE 8501

# Health check
# This tells Docker/OrbStack if the container is healthy
# It checks if Streamlit's health endpoint responds
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Set default Streamlit configuration
# These can be overridden with environment variables or streamlit config files
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run the Streamlit application
# CMD is the default command when container starts
# Users can override this if needed
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
