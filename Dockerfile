FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Set non-sensitive environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

# Install build dependencies for asyncmy (Cython extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create venv and install deps
RUN uv venv /venv \
 && UV_PROJECT_ENVIRONMENT=/venv uv sync --frozen --no-dev

# Copy application code
COPY src ./src
COPY scripts ./scripts

# Use venv by default
ENV PATH="/venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Run the application
CMD ["/venv/bin/python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
