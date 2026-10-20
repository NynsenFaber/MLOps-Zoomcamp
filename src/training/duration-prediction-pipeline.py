"""
Run it with (example):
    uv run --env-file .env duration-prediction-pipeline.py --year 2026 --month 4
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import skops.io as sio
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.metrics import root_mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline

import mlflow
from mlflow import MlflowClient
from prefect import flow, get_run_logger, task

# Config: tracking URI comes from MLFLOW_TRACKING_URI in .env.
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "nyc-taxi-experiment_xgboost")
MODEL_NAME = os.getenv("MODEL_NAME", "nyc_taxi_xgb_model")
RMSE_THRESHOLD = float(os.getenv("RMSE_THRESHOLD", "10.0"))
MODELS_FOLDER = Path(os.getenv("MODELS_FOLDER", "models"))

FEATURES = ["PU_DO", "trip_distance"]
TARGET = "duration"
SKOPS_TRUSTED_TYPES = ["xgboost.core.Booster", "xgboost.sklearn.XGBRegressor"]


@task(retries=3, retry_delay_seconds=2)
def read_dataframe(year: int, month: int) -> pd.DataFrame:
    """Read one month of NYC green taxi data, compute duration, and build the PU_DO feature."""
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_{year}-{month:02d}.parquet"
    df = pd.read_parquet(url)

    df["duration"] = (
        df.lpep_dropoff_datetime - df.lpep_pickup_datetime
    ).dt.total_seconds() / 60
    df = df[(df.duration >= 1) & (df.duration <= 60)].copy()

    categorical = ["PULocationID", "DOLocationID"]
    df[categorical] = df[categorical].astype(str)
    df["PU_DO"] = df["PULocationID"] + "_" + df["DOLocationID"]

    return df


def build_pipeline(params: dict):
    preprocessor = ColumnTransformer(
        [
            ("pu_do", OneHotEncoder(handle_unknown="ignore"), ["PU_DO"]),
            ("num", "passthrough", ["trip_distance"]),
        ]
    )
    return make_pipeline(preprocessor, xgb.XGBRegressor(**params))

@task
def save_pipeline(pipeline, path: Path):
    """Save the pipeline to a file using skops."""
    sio.dump(pipeline, path)
    print(f"Saved pipeline to {path}")


@task
def train_and_evaluate(df_train: pd.DataFrame, 
                       df_val: pd.DataFrame, 
                       year: int, 
                       month: int) -> Pipeline:
    logger = get_run_logger()

    params = {
        "learning_rate": 0.09585355369315604,
        "max_depth": 30,
        "min_child_weight": 1.060597050922164,
        "objective": "reg:squarederror",
        "reg_alpha": 0.018060244040060163,
        "reg_lambda": 0.011658731377413597,
        "random_state": 42,
        "n_estimators": 30,
    }

    X_train, y_train = df_train[FEATURES], df_train[TARGET].values
    X_val, y_val = df_val[FEATURES], df_val[TARGET].values

    with mlflow.start_run():
        mlflow.set_tags({"train_period": f"{year}-{month:02d}"})
        mlflow.log_params(params)

        pipeline = build_pipeline(params)
        pipeline.fit(X_train, y_train)

        # Gate: evaluate before logging or registering anything
        val_rmse = root_mean_squared_error(y_val, pipeline.predict(X_val))
        baseline_rmse = root_mean_squared_error(y_val, np.full_like(y_val, y_train.mean()))
        mlflow.log_metrics({"val_rmse": val_rmse, "baseline_rmse": baseline_rmse})
        logger.info(f"val_rmse={val_rmse:.2f}, baseline_rmse={baseline_rmse:.2f}")

        if val_rmse > RMSE_THRESHOLD or val_rmse >= baseline_rmse:
            raise ValueError(
                f"Validation RMSE {val_rmse:.2f} failed the gate "
                f"(threshold {RMSE_THRESHOLD}, baseline {baseline_rmse:.2f}). Model not registered."
            )

        model_info = mlflow.sklearn.log_model(
            sk_model=pipeline,
            name="nyc_taxi_pipeline",
            input_example=X_val.head(5),
            skops_trusted_types=SKOPS_TRUSTED_TYPES,
            registered_model_name=MODEL_NAME,
        )

        version = model_info.registered_model_version
        MlflowClient().set_registered_model_alias(MODEL_NAME, "staging", version)
        logger.info(f"Registered {MODEL_NAME} v{version} with alias 'staging'")

        return pipeline


@flow(name="NYC-Taxi-MLflow3-Flow")
def run(year: int, month: int) -> None:
    mlflow.set_experiment(EXPERIMENT_NAME)

    val_period = pd.Period(f"{year}-{month:02d}", freq="M") + 1
    df_train = read_dataframe(year, month)
    df_val = read_dataframe(val_period.year, val_period.month)

    pipeline = train_and_evaluate(df_train, df_val, year, month)

    # save local copy
    MODELS_FOLDER.mkdir(exist_ok=True)
    save_pipeline(pipeline, MODELS_FOLDER / "nyc_taxi_pipeline.skops")

    return 


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train a model to predict taxi trip duration.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    args = parser.parse_args()

    run_id = run(year=args.year, month=args.month)