FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/

WORKDIR /mlflow-server

COPY pyproject.toml uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --no-dev --no-cache

EXPOSE 5001
CMD ["mlflow", "server", \
     "--backend-store-uri", "sqlite:///mlflow/mlflow.db", \
     "--artifacts-destination", "./mlflow/mlartifacts", \
     "--host", "0.0.0.0", \
     "--port", "5001"]