# Rolling update
In the previous example, when a new model in MLFlow is selected to be a `@champion` the app does not automatically load it. It only download the model which is `@champion` at starting time. The only way to upload the new model in the app is the restart it, but this would create problem for the requests arriving during the restart.

The best approach is provide a **rolling update**: a new copy of the app starts with the new model, traffic is redirected to it, then the old app is closed. This can be done using **Kubernetes**.

The underlying idea of a rolling update is that as soon as a new model is deployed a new pod is created, the model is loaded, and when it is healthy traffic is redirected to it closing the old pod. To make things simple we will run only one pod and when a model must be deployed a second pod will be created.

## Minikube

I am going to use [minikube](https://minikube.sigs.k8s.io/docs/) to test my kubernetes cluster locally. It creates a containerized node on my local machine simulating a kubernetes cluster (control plane and nodes with pods).

To start the cluster using docker-desktop as driver
```bash
minikube start --driver docker
```

One started the cluster we can see the nodes that are available using kubernetes CLI 

```bash
kubectl get nodes
```

We should get something like

```bash
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   20h   v1.37.0
```

Indicating that the control plane is ready, thus the kubernetes API is ready to create additional nodes and pods.

## Cluster and Communicationn with MLFlow

To make things simple, we only put in the cluster the web-app, leaving outside both the MLFlow server and the Prefect server. The web-app does not need to communicate with the Prefect server, but it must communicate to the MLFlow server. Pods can't use Compose's name `mlflow-server`, because the cluster has its own DNS. This requires to set a `Service` with external name so that when the node in the cluster wants to connect to `http://mlflow-server:5001` it actually connects to the right docker container

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mlflow-server
spec:
  type: ExternalName
  externalName: host.minikube.internal
```

`host.minikube.internal` is Minikube's special name for the machine running the cluster. Thus, with this file we deescribe a cluster that when tries to connect to `http://mlflow-server:5001` it acctually connect to `http://host.minikube.internal:5001` while still keeping the mmlflow header.

## Declaring the Node in Kubernetes 

The web app is described by a **Deployment** in `web-service.yaml`. A Deployment tells Kubernetes how many pods of the app to run and how to replace them when we update it. The first part:


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-service
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
```

The Deployment is named `web-service`. With `replicas: 1`, Kubernetes keeps one pod running at all times, starting a new one if it crashes. Next, we define the rolling update strategy with `maxUnavailable` we declare how many pods may be missing below replicas during the rollout, with `maxSurge` instead how many extra pods may exist above replicas during the rollout. As said, we require an additional pod during the rollout.

Next we need to define the blueprint, which is an instruction that teach Kubernetes how to construct or reconstruct a pod. It is declared using `template:`

```yaml
template:
    metadata:
      labels:
        app: web-service
    spec:
      containers:
        - name: web-service
          image: web-service:v1
          imagePullPolicy: Never
          # Environmental variable of the app, how to reach MLFlow.
          env:
            - name: MLFLOW_TRACKING_URI
              value: http://mlflow:5001
          ports:
            - containerPort: 9696
          readinessProbe:
            httpGet:
              path: /health
              port: 9696
            periodSeconds: 5
            timeoutSeconds: 2
```

With metadata label we apply a common label to all the pods. 

> With imagePullPolicy: Never we tell to not download the image but use only the one in the minikube image store. In this example I am not publishing the image of the web-app, so we need to load it directly to the Minikube image store using `minikube image load web-service:v1`

Finally, the readiness probe is made so that Kubernetes can check the health status (defined in the next section) of the pod every 5 seconds. If it answers within 2 seconds, the pod is ready.

### Communicating with the App running in a POD
How can we connect to the pod running in the kubernetes cluster? We need to define a Service for the web-app

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  type: LoadBalancer
  selector:
    app: web-service
  ports:
    - port: 9696
      targetPort: 9696
```
With `LoadBalancer` we create an external adress so that the application is reachable outside the cluster.

## Preparing the app for rolling updates
We add a `/health` route to the app that gives information about its status and which model it has loaded. Next we have instruction where to pull the image of the container to create.

## Running the app

First we build and run MLFlow and Prefect server and build the web-app image

```bash
docker compose up mlflow-server prefect-server -d
docker build -t web-service:v1 .
```

then we start the kubernetes cluster using minikube and load the web-service image

```bash
minikube start --driver docker
minikube image load web-service:v1
```

Once the control plane is created, we can send our instructions to the kubernetes API

```bash
kubectl apply -f k8s/
```

You should see a pod running by writing `kubectl get pods`. Now, to access the minikube cluster we need to open a tunnel so that the computer can send requets, in a different terminal (that must be open while tunneling) run

```bash
minikube tunnel
```

Now `make test` should work.

### Performing the rollout

Suppose a new `@champion` has been selected in MLFlow, then a rollout is done by running

```bash
kubectl rollout restart deployment/web-service
```

For testing run `make stress-test`, change a `@champion` model in MLFlow, run `make deploy` and observe

```
fabrizioboninsegna@MacBookPro 3_web-service-rolling-update % make stress-test
uv run stress-test.py
Model version: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
New model version detected: 5
New model version detected: 4
```

This is normal behaviour, during a rollout two pods exist simultaneosly so each requets can go to either port. Importantly, at the end only one pod with the new model is lives.