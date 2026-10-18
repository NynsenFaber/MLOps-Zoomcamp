# MLflow

Usually we need to set a tracking uri

```python
import mlflow

mlflow.set_tracking_uri('http://127.0.0.1:5000') 
```
For a local host. Best practice is to put the tracking uri in the `.env` file and use this script to run the web-app

```bash
	uv run --env-file .env gunicorn --bind=0.0.0.0:9696 predict:app
```

With `--env-file .env` we say to look into the private `.env` file, here mlflow will automatically look for `MLFLOW_TRACKING_URI=...` and set it.

