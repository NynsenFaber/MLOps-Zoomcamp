# Default values, overridable from the command line
YEAR ?= 2026
MONTH ?= 4

.PHONY: mlflow-start prefect-start train build-run-mlflow

mlflow-start:  ## Start the MLflow tracking server on port 5001
	uv run mlflow server \
		--backend-store-uri sqlite:///mlflow/mlflow.db \
		--artifacts-destination ./mlflow/mlartifacts \
		--port 5001

prefect-start:  ## Start the Prefect server on port 4200
	uv run prefect server start --port 4200

train:  ## Run the training flow (override with YEAR=... MONTH=...)
	uv run --env-file .env src/training/duration-prediction-pipeline.py --year $(YEAR) --month $(MONTH)

build-run-mlflow:  ## Build and run the MLflow server in a Docker container
	cd mlflow-server && \
	docker build -t mlflow-server . && \
	docker run --rm -p 127.0.0.1:5001:5001 -v "$(CURDIR)/mlflow-server/mlflow:/mlflow-server/mlflow" mlflow-server