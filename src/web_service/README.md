- Create virtual env using uv
- Creating a script for predicting
- Putting the script into a flask app
- Packaging the app to Docker

# Create virtual environment using uv
The web service gets its own small environment separated from the main one used for training. 

In the `src/web_service` folder run to create the separate venv

```bash
uv init --bare --no-workspace --python 3.14
```
Then add the dependencies

```bash
uv add <dependencies> flask gunicorn
```
We will use both flask and gunicorn (for the production ready server).

> In `test.py` we are using `request`. We can add it to the venv environment for the web-app but only as a dev tool so that when we deploy in production the web-app this tool would not be present
```bash
uv add --dev requests
```

# Flask
It is a simple framework to deploy web-app application in python. In this project we use

```python
from flask import Flask, request, jsonify

app = Flask('<name_of_the_app')

@app.route('/predict', methods=['POST'])
def predict_endpoint() -> dict:
    ...
    return jsonify(...)
```

With `Flask` we create an app. The decorator `@app.route` creates a web endpoint `\predict` with restrict access on POST requests (standard method when a client needs to send data to a server). When the endpoint is called the function decorated is triggered. The final output is convertend into JSON with `jsonify`

# Web server
We use `gunicorn` to initilize a local server by running (Flusk built in server is only meant for local development). Gunicorn is a production-grade server that spins up multiple parallel "worker" processes, allowing your application to handle many simultaneous requests and automatically restarting workers if they crash.

```bash
uv run gunicorn --bind=0.0.0.0:9696 predict:app
```

This will run the web-app on all network interfaces (0.0.0.0), so that anyone can contact it, on port 9696, notice the `predict:app` indicating that the application `app` must be searched into `predict.py`

# Docker

Finally we crate a docker image so that the web-app runs everywhere in a fixed container

```bash
docker build -t <image_name> .
```

with `-t` we specify the name of the image, and with final `.` indicates to serach `Dockerfile` in the current folder

The to run it

```bash
docker run -it --rm -p 9696:9696 <image_name>
```

With `-it` we want interactive mode (so we can stop using ctrl+C the app in the terminal), with `--rm` we say to delete the container when finish. With `-p` we map the port on our host machine to the port exposed inside the container (Dockerfile contains `EXPOSE 9696`), meaning that trafic on the local port 9696 is forwarded to the web-app running on port 9696 inside Docker