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
	docker build -t nameko-multi-resion-base -f docker/base.docker .;

build-wheelbuilder:
	docker build -t $(SERVICE_NAME)-builder -f docker/build.docker .;

run-wheelbuilder:
	docker run --rm \
		-v "$$(pwd)":/application -v "$$(pwd)"/wheelhouse:/wheelhouse \
		$(SERVICE_NAME)-builder;

build-service:
	docker build -t $(SERVICE_NAME):$(TAG) \
	-f docker/run.docker .;

build-rabbit:
	docker build -t rabbitmq:3.5.6-federation \
	-f docker/rabbit.docker .;

build-all: build-base build-wheelbuilder run-wheelbuilder build-service build-rabbit

run-app:
		docker rm -f $(SERVICE_NAME)
		docker run -it -p 8090:8000 \
		--link rabbit:rabbit -e RABBIT_HOST="rabbit" \
		-e RABBIT_PORT="5672" -e RABBIT_MANAGEMENT_PORT="15672" \
		--name $(SERVICE_NAME) $(SERVICE_NAME):$(TAG)

rabbit:
	docker run -d -p 5672:5672 -p 15672:15672 -p 53160:53160/udp --hostname rabbit \
	-e RABBITMQ_ERLANG_COOKIE='24261958953861120' --restart always \
	--name rabbit rabbitmq:3.5.6-federation
