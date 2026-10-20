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
import optuna
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
N_TRIALS = int(os.getenv("N_TRIALS", "50"))
FIXED_PARAMS = {"objective": "reg:squarederror", "random_state": 42}

def build_pipeline(params: dict):
    preprocessor = ColumnTransformer(
        [
            ("pu_do", OneHotEncoder(handle_unknown="ignore"), ["PU_DO"]),
            ("num", "passthrough", ["trip_distance"]),
        ]
    )
    return make_pipeline(preprocessor, xgb.XGBRegressor(**params))


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

@task
def save_pipeline(pipeline, path: Path):
    """Save the pipeline to a file using skops."""
    sio.dump(pipeline, path)
    get_run_logger().info(f"Saved pipeline to {path}")

@task
def tune_params(X_train, y_train, X_val, y_val, parent_run_id: str) -> tuple[Pipeline, float, str]:
    """Search XGBoost hyperparameters with Optuna, minimizing validation RMSE.

    Each trial is logged as an MLflow child run of parent_run_id.
    Returns the already-fitted best pipeline, its val RMSE, and its child run ID.
    """
    best = {"val_rmse": float("inf")}

    def objective_(trial: optuna.Trial) -> float:
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 30),
            "min_child_weight": trial.suggest_float("min_child_weight", 1e-3, 10.0, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 1.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 1.0, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 10, 100),
            **FIXED_PARAMS,
        }
        with mlflow.start_run(run_name=f"trial-{trial.number}", parent_run_id=parent_run_id, nested=True) as child:
            mlflow.log_params(params)
            pipeline = build_pipeline(params).fit(X_train, y_train)
            val_rmse = root_mean_squared_error(y_val, pipeline.predict(X_val))
            mlflow.log_metric("val_rmse", val_rmse)
            get_run_logger().info(f"Trial {trial.number}: val_rmse={val_rmse:.2f}")
        if val_rmse < best["val_rmse"]:
            best.update(val_rmse=val_rmse, pipeline=pipeline, run_id=child.info.run_id)
        return val_rmse

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective_, n_trials=N_TRIALS)
    get_run_logger().info(f"Best trial val_rmse={study.best_value:.2f}, params={study.best_params}")
    return best["pipeline"], best["val_rmse"], best["run_id"]


@task
def train_and_evaluate(df_train: pd.DataFrame, 
                       df_val: pd.DataFrame, 
                       year: int, 
                       month: int) -> None:

    mlflow_client = MlflowClient()

    X_train, y_train = df_train[FEATURES], df_train[TARGET].values
    X_val, y_val = df_val[FEATURES], df_val[TARGET].values

    with mlflow.start_run() as run:
        mlflow.set_tags({"train_period": f"{year}-{month:02d}"})

        # Tune hyperparameters with Optuna, each trial a child run
        pipeline, val_rmse, best_run_id = tune_params(X_train, y_train, X_val, y_val, run.info.run_id)
        mlflow.set_tag("best_run_id", best_run_id)
        mlflow_client.set_tag(best_run_id, "best_trial", "true")

        # ---- Gate: evaluate before logging or registering anything -----
        # Baseline as the mean of the training target (Dummy Regressor)
        baseline_rmse = root_mean_squared_error(y_val, np.full_like(y_val, y_train.mean()))
        mlflow.log_metric("baseline_rmse", baseline_rmse)
        mlflow.log_metric("best_val_rmse", val_rmse)
        get_run_logger().info(f"val_rmse={val_rmse:.2f}, baseline_rmse={baseline_rmse:.2f}")

        if val_rmse > RMSE_THRESHOLD or val_rmse >= baseline_rmse:
            raise ValueError(
                f"Validation RMSE {val_rmse:.2f} failed the gate "
                f"(threshold {RMSE_THRESHOLD}, baseline {baseline_rmse:.2f}). Model not registered."
            )

        # Log the model into the best child run, next to its params and val_rmse
        with mlflow.start_run(run_id=best_run_id, nested=True):
            model_info = mlflow.sklearn.log_model(
                sk_model=pipeline,
                name="nyc_taxi_pipeline",
                input_example=X_val.head(5),
                skops_trusted_types=SKOPS_TRUSTED_TYPES,
                registered_model_name=MODEL_NAME,
                tags={"train_period": f"{year}-{month:02d}",
                      "stage": "staging"},
            )

        version = model_info.registered_model_version
        get_run_logger().info(f"Registered {MODEL_NAME} v{version} with alias 'staging'")

        return 


@flow(name="NYC-Taxi-MLflow3-Flow")
def run(year: int, month: int) -> None:
    mlflow.set_experiment(EXPERIMENT_NAME)

    val_period = pd.Period(f"{year}-{month:02d}", freq="M") + 1
    df_train = read_dataframe(year, month)
    df_val = read_dataframe(val_period.year, val_period.month)

    train_and_evaluate(df_train, df_val, year, month)

    return 


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train a model to predict taxi trip duration.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    args = parser.parse_args()

    run_id = run(year=args.year, month=args.month)