import requests

ride = {
    "PULocationID": [1],
    "DOLocationID": [2],
    "trip_distance": [3.0],
}

url = "http://localhost:9696/predict"
response = requests.post(url, json=ride)
print(response.json())
