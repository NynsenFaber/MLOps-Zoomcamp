# MLOps Level

1) `No Automation`: Essentially jupyter notebooks, no experiment tracking, no model, no model registry

2) `DevOps but no MLOps`: There is some level of automation, like automated releases, unit tests, CI/CD, operational metrics. No ML specific automation.

3) `Automated Training`: As thte title says, there is a training pipeline, an experiment tracking so you now which model is in production, there is a model registry.

4) `Automated Deployment`: No human to deploy a model. There is an ML Platform to deploy models. We might have A/B tests so that automatically the ML Platform decides which model is better.Models are monitored at this stage.

5) `Full MLOps operations`: Everything is automated. Model monitoring is automated and triggers new training and new deployment.

# SSH

To enter into the hidden `ssh` folder 
```bash
cd ~/.ssh 
```

### Downloading and restict a .pem key
When creating a key on AWS you must download it and move it to the `.ssh/` folder

```bash
mv ~/Downloads/<key-name>.pem ~/.ssh/
```

Then you need to restrict the key permission so that it can be read only by you

```bash
chmod 400 ~/.ssh/<key-name>.pem 
```

With `chmod 400` only the file owner can read the key, and no one can either write it or execute it. 400 stands for read only. 


### Connecting
Connect to external machine
```bash
ssh -i ~/.ssh/<my_key.pem> <os_username>@<public_ip_address>
```

You can also modify the configuration so to make this easier

```bash
nano ~/.ssh/config
```

and write a command

```
Host <command>
  HostName <public IP adress>
  User <cloud name machine>
  IdentityFile ~/.ssh/<your_key>.pem
  StrictHostKeyChecking no
```

So then you can just run

```bash
ssh <command>
```

With this config then it is easy to use VSCode with the remote extensions to connect to the cloud server.

# Experiment Tracking

## MLflow - experiments tracking

>Keeping track of hyperparameters, losses, training and val dataset.

To use a local database for the UI run in the python script to set up the database
```python
import mlflow

mlflow.set_tracking_uri("sqlite:///<path_of_database_folder>/mlflow.db")
mlflow.create_experiment(
    "<experiment_name",
    artifact_location="file:<path_of_database_folder>",
)
mlflow.mlflow.set_experiment("experiment_name")
```

and then to run the UI

```bash
mlflow ui --backend-store-uri sqlite:///<path_of_database_folder>/mlflow.db
```

> Good to put in `.gitignore` the local database for experiment and models tracking, as it contains large files and and creates constant merge conflicts on iterative experiments.

### Model hyperparameter
There are many libraries that we can use to search the best hyperparameters

- `hyperopt`: 
- `optuna`: The standard choice thanks to its workflow being defined-by-run (the parameter space is constructed dynamically during execution).
## MLFlow - model tracking

> Retrieve models that worked well in the past

### Model Registry
It is the place where all the models that are production ready are stored. We have different stages:

- Staging: Pre-production and trail versions
- Production: Current model that is used
- Archive: Previous models

This is essentially a database, so to actually deploy the model some CI/CD is needed.

> Model registry is not possible in the case you use your local file system for the artifacts and backend store. If you use a SQLite backend store in your local system than it is ok.

## Configuring MLFlow

#### Scenario 1: One Data Scientist working alone. 

Everything is stored locally (SQLite database). No tracking server is needed.

#### Scenario 2: Cross functional team, but only one Data Scientist

Here a tracking server is necessary, but locally. The backend a SQLite DB is good, so you can use model registry. Artficats can be stored locally.

#### Scenario 3: Multiple Data Scientist working on multiple ML modle

This scenario requires a tracking server which is remote (e.g. EC2 AWS). The Backend can be PostgreSQL, use RDS in AWS (SQLite works well if only one user uses it). The Artifacts store must be remotely as well, a standard choice in AWS is S3 bucket.

The standard way in AWS is to instantiate a server using EC2 (enable http connection with port 5000 for MLFlow ui), then start a S3 bucket, a PostgreSQL and connect it to the EC2. The run the server on the EC2 machine (connect to it using SSH for example), start a project folder and instantiate a uv environment

```bash
uv venv
source .venv/bin/activate
uv pip install mlflow boto3 psycopg2-binary
```

configure the aws cli using a secret key

```bash
aws config
```

finally to run the server

```bash
mlflow server -h 0.0.0.0 -p 5000 --backend-store-uri postgresql://DB_USER:DB_PASSWORD@DB_ENDPOINT:5432/DB_NAME --default-artifact-root s3://S3_BUCKET_NAME
```

to see the MLflow UI you can then run on your browser

```bash
http://<EC2_PUBLIC_DNS>:5000
```

and to connect to the mlflow client on your code

```python
import mlflow
import os

os.environ["AWS_PROFILE"] = "" # fill in with your AWS profile (usually default is good).

TRACKING_SERVER_HOST = "" # fill in with the public DNS of the EC2 instance
mlflow.set_tracking_uri(f"http://{TRACKING_SERVER_HOST}:5000")
```

# Workflow Orchestration
There are tools to make sure that the entire pipeline works properly remotely.

- Airflow
- Prefect
- Mage

There are tools specific for ML Pipelines

- Kubeflow pipelines
- MLFlow pipelines

