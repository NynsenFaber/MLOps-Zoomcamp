.PHONY: test start-app build

test:
	uv run test.py

# production ready server using gunicorn
# and localhost binding
start-app:
	uv run --env-file .env gunicorn --bind=0.0.0.0:9696 predict:app

build:
	docker build -t duration-prediction-app-v1 .

# run in interactive mode with port mapping
# --rm removes the container after it exits
run:
	docker run -it --rm -p 9696:9696 duration-prediction-app-v1

