# docker-machine create --driver virtualbox eu
#
# docker-machine env eu
#
# eval $(docker-machine env eu)
#
# switch back
#
# unset DOCKER_TLS_VERIFY
# unset DOCKER_CERT_PATH
# unset DOCKER_MACHINE_NAME
# unset DOCKER_HOST

SERVICE_NAME ?= products-service
TAG ?= dev

# Build Docker Images

build-base:
	docker build -t nameko-multi-resion-base -f docker/docker.base .;

build-wheelbuilder:
	docker build -t $(SERVICE_NAME)-builder -f docker/docker.build .;

run-wheelbuilder:
	docker run --rm \
		-v "$$(pwd)":/application -v "$$(pwd)"/wheelhouse:/wheelhouse \
		$(SERVICE_NAME)-builder;

build-service:
	docker build -t $(SERVICE_NAME):$(TAG) \
	-f docker/docker.run .;

build-all: build-base build-wheelbuilder run-wheelbuilder build-service

run-app:
		docker rm -f $(SERVICE_NAME)
		docker run -it -d -p 8090:8000 \
		--link rabbit:rabbit -e RABBIT_HOST=rabbit \
		--name $(SERVICE_NAME) $(SERVICE_NAME):$(TAG)
