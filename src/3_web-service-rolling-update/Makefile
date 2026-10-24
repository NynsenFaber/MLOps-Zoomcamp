build:
	docker compose up mlflow-server prefect-server -d
	docker build -t web-service:v1 .
	minikube start --driver docker
	minikube image load web-service:v1
	kubectl apply -f k8s/

activate:
	minikube tunnel

deploy: 
	kubectl rollout restart deployment/web-service

test:
	uv run test.py

stress-test:
	uv run stress-test.py