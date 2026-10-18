FROM python:3.14-slim

# Install uv 
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-dev --no-cache

# Copy the application code
COPY predict.py ./
COPY models/ ./models

# Expose the port and run the application
EXPOSE 9696

# Use gunicorn to run the application
CMD ["gunicorn", "--bind=0.0.0.0:9696", "predict:app"]