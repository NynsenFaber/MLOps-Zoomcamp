# Default values, overridable from the command line
YEAR ?= 2026
MONTH ?= 4

.PHONY: mlflow prefect train

mlflow:  ## Start the MLflow tracking server on port 5001
	uv run mlflow server \
		--backend-store-uri sqlite:///mlflow/mlflow.db \
		--artifacts-destination ./mlflow/mlartifacts \
		--port 5001

prefect:  ## Start the Prefect server on port 4200
	uv run prefect server start --port 4200

train:  ## Run the training flow (override with YEAR=... MONTH=...)
	uv run --env-file .env src/duration-prediction-pipeline.py --year $(YEAR) --month $(MONTH)