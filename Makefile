# Default values, overridable from the command line
YEAR ?= 2026
MONTH ?= 4

.PHONY: mlflow-start prefect-start train build-run-mlflow

mlflow-start:  ## Start the MLflow tracking server on port 5001
	uv run mlflow server \
		--backend-store-uri sqlite:///mlflow/mlflow.db \
		--artifacts-destination ./mlflow/mlartifacts \
		--port 5001

test:
	cd src/2_web-service-mlflow && uv run test.py

prefect-start:  ## Start the Prefect server on port 4200
	uv run prefect server start --host 0.0.0.0 --port 4200

train:  ## Run the training flow (override with YEAR=... MONTH=...)
	uv run --env-file .env src/training/duration-prediction-pipeline.py --year $(YEAR) --month $(MONTH)

build-mflow:
	docker build -t duration-prediction:v1 src/web-service-mlflow