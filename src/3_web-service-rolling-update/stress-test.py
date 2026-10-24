import requests

ride = {
    "PULocationID": [1],
    "DOLocationID": [2],
    "trip_distance": [3.0],
}

url = "http://localhost:9696/predict"
response = requests.post(url, json=ride)
model_version = response.json().get("model_version", "unknown")
print(f"Model version: {model_version}")
while True:
    try:
        response = requests.post(url, json=ride)
        new_model_version = response.json().get("model_version", "unknown")
        if new_model_version != model_version:
            model_version = new_model_version
            print(f"New model version detected: {model_version}")
    except Exception as e:
        print(f"Error occurred while making request: {e}")

