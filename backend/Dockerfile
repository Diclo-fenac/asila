# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install uv (using a newer stable version for best performance)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --frozen --no-dev

# Stage 2: Final Production Image
FROM python:3.11-slim

# Create a non-root user for security
RUN useradd -m asila
USER asila

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=asila:asila /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=asila:asila . .

# Expose API port
EXPOSE 8000

# Command to run the application using uvicorn in production mode (no reload)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
