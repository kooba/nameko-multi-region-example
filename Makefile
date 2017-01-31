SERVICE_NAME ?= nameko-multi-region-example-products
RABBIT_IMAGE_NAME ?= nameko-multi-region-example-rabbitmq
TAG ?= latest
REGIONS ?= europe asia america

# Build Docker Images

build-base:
	docker build -t nameko-multi-region-base -f docker/base.docker .;

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
	docker build -t $(RABBIT_IMAGE_NAME):$(TAG) \
	-f docker/rabbit.docker .;

build-all: build-base build-wheelbuilder run-wheelbuilder build-service build-rabbit

push-to-docker-hub:
	docker tag $(SERVICE_NAME):$(TAG) jakubborys/$(SERVICE_NAME):$(TAG)
	docker tag $(RABBIT_IMAGE_NAME):$(TAG) jakubborys/$(RABBIT_IMAGE_NAME):$(TAG)
	docker push jakubborys/$(SERVICE_NAME):$(TAG)
	docker push jakubborys/$(RABBIT_IMAGE_NAME):$(TAG)

# Run rabbitmq container

rabbit:
	docker run -d -p 5672:5672 -p 15672:15672 -p 53160:53160/udp --hostname rabbit \
	-e RABBITMQ_ERLANG_COOKIE='24261958953861120' \
	--name $(RABBIT_IMAGE_NAME) $(RABBIT_IMAGE_NAME):$(TAG)

# Run service container

run-app:
	docker run -d -p 8090:8000 \
	--link rabbit:$(RABBIT_IMAGE_NAME) -e RABBIT_HOST="rabbit" \
	-e RABBIT_PORT="5672" -e RABBIT_MANAGEMENT_PORT="15672" \
	--name $(SERVICE_NAME) $(SERVICE_NAME):$(TAG)

create-machines:
	for region in $(REGIONS) ; do \
		docker-machine create --driver virtualbox $$region; \
	done

deploy:
	for region in $(REGIONS) ; do \
		eval $$(docker-machine env $$region) && docker-compose -f docker-compose/common.yml -f docker-compose/$$region.yml up -d; \
	done

cleanup-hosts:
	for region in europe asia america ; do \
		eval $$(docker-machine env $$region) && docker rm -f $(SERVICE_NAME) && docker rm -f $(RABBIT_IMAGE_NAME); \
	done

list-services:
	for region in europe asia america ; do \
		eval $$(docker-machine env $$region) && docker ps; \
	done

docker-command:
	eval $$(docker-machine env $(R)) && $(CMD)
