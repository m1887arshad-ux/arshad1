# ============================================================================
# Bharat Biz-Agent Backend — Production-Safe Standalone Dockerfile
# ============================================================================
# 
# HACKATHON SUBMISSION REQUIREMENTS:
# - Must build with: docker build -t bharat-biz .
# - Must run with: docker run -p 8000:8000 bharat-biz
# - Must work in isolated Linux container without external dependencies
# - Backend must be accessible at http://localhost:8000/docs
#
# ARCHITECTURE:
# - FastAPI backend with Telegram bot integration
# - SQLite database (container-safe path)
# - Environment-based configuration (no hardcoded secrets)
# - Graceful degradation when optional services unavailable
# ============================================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# Install system dependencies
# - curl: for Docker health checks
# - minimal tooling for production
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entire backend code
COPY backend/ .

# Configure container-safe SQLite database path
# This path is inside the container and does not depend on host filesystem
ENV DATABASE_URL=sqlite:///./database.db

# Default environment variables (can be overridden at runtime)
# These provide safe fallbacks when secrets are not provided
ENV SECRET_KEY="" \
    TELEGRAM_BOT_TOKEN="" \
    GROQ_API_KEY="" \
    CORS_ALLOW_ORIGIN="*"

# Expose port 8000 for FastAPI
EXPOSE 8000

# Health check for container orchestration
# Checks if FastAPI is responding on /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
# - host 0.0.0.0: Bind to all interfaces (required for Docker port mapping)
# - port 8000: Standard FastAPI port
# - app.main:app: FastAPI app instance from main.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
