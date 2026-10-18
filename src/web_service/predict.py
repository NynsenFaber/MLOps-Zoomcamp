from pathlib import Path
from skops.io import load
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify

MODEL_PATH = Path(__file__).parent / "models" / "nyc_taxi_pipeline.skops"
SKOPS_TRUSTED_TYPES = ["xgboost.core.Booster", "xgboost.sklearn.XGBRegressor"]

# loading the model using skops with trusted types
model = load(MODEL_PATH, trusted=SKOPS_TRUSTED_TYPES)

def preprocess_input(ride: dict) -> pd.DataFrame:
    """Preprocess the input features into a DataFrame suitable for prediction."""
    try:
        features = {}
        features['trip_distance'] = ride.get("trip_distance", [])
        features['PU_DO'] = [str(pu) + "_" + str(do) for pu, do in 
                             zip(ride.get("PULocationID", []), ride.get("DOLocationID", []))  ]
        df = pd.DataFrame(features, columns=["PU_DO", "trip_distance"])
        return df
    except Exception as e:
        print(f"Error occurred while preprocessing input: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

def predict(features: dict) -> np.ndarray:
    """Make predictions using the loaded model."""
    df = preprocess_input(features)
    if df.empty:
        print("Input DataFrame is empty. Cannot make predictions.")
        return np.array([])  # Return an empty array if preprocessing failed
    try:
        predictions = model.predict(df)
        return predictions
    except Exception as e:
        print(f"Error occurred during prediction: {e}")
        return np.array([])  # Return an empty array on prediction error

app = Flask('duration-prediction')

@app.route('/predict', methods=['POST'])
def predict_endpoint() -> dict:
    """API endpoint for making predictions."""
    ride = request.get_json()
    try:
        predictions = predict(ride)
        return jsonify({"duration": predictions.tolist()})
    except Exception as e:
        print(f"Error occurred in predict_endpoint: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=9696)