SERVICE_NAME ?= nameko-multi-region-example-products
RABBIT_NAME ?= nameko-multi-region-example-rabbitmq
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
	docker build -t $(RABBIT_NAME):$(TAG) \
	-f docker/rabbit.docker .;

build-all: build-base build-wheelbuilder run-wheelbuilder build-service build-rabbit

push-to-docker-hub:
	docker tag $(SERVICE_NAME):$(TAG) jakubborys/$(SERVICE_NAME):$(TAG)
	docker tag $(RABBIT_NAME):$(TAG) jakubborys/$(RABBIT_NAME):$(TAG)
	docker push jakubborys/$(SERVICE_NAME):$(TAG)
	docker push jakubborys/$(RABBIT_NAME):$(TAG)

# Provision Docker Hosts for each Region

create-machines:
	@for region in $(REGIONS) ; do \
		docker-machine create --driver virtualbox $$region; \
	done

deploy-images:
	@for region in $(REGIONS) ; do \
		eval $$(docker-machine env $$region) && docker-compose -f docker-compose/common.yml -f docker-compose/$$region.yml up -d; \
	done

# RabbitMQ Federation Setup

federation-upstreams:
	@for region in $(REGIONS) ; do \
		eval $$(docker-machine env $$region) ; \
		regions=($(REGIONS)) remove=$$region && upstream_hosts="$${regions[@]/$$remove}" ; \
			for upstream_host in $$upstream_hosts ; do \
				docker exec $(RABBIT_NAME) sh -c \
				"rabbitmqctl set_parameter federation-upstream  $$upstream_host-upstream \
				'{\"uri\":\"amqp://$$(docker-machine ip $$upstream_host):5672\"}'" ; \
			done \
	done

federation-exchange-policy:
	@for region in $(REGIONS) ; do \
		eval $$(docker-machine env $$region) ; \
		docker exec $(RABBIT_NAME) sh -c "rabbitmqctl set_policy --apply-to exchanges \
		federated-exchanges \".*\.events$$\" '{\"federation-upstream-set\":\"all\"}'" ; \
	done

federation-queue-policy:
	@for region in $(REGIONS) ; do \
		eval $$(docker-machine env $$region) ; \
		docker exec $(RABBIT_NAME) sh -c "rabbitmqctl set_policy --apply-to queues \
		federated-queues \"^(fed\..*)$$\" '{\"federation-upstream-set\":\"all\"}'" ; \
	done

setup-federation: federation-upstreams federation-exchange-policy federation-queue-policy

# Handy utility commands 

list-services:
	@for region in $(REGIONS) ; do \
		eval $$(docker-machine env $$region) && docker ps; \
	done

docker-command:
	@eval $$(docker-machine env $(R)) && $(CMD)

start-hosts:
	@for region in $(REGIONS) ; do \
		docker-machine start $$region; \
		docker-machine regenerate-certs $$region; \
	done

stop-hosts:
	@for region in $(REGIONS) ; do \
		docker-machine stop $$region; \
	done

cleanup-hosts:
	@for region in $(REGIONS) ; do \
		eval $$(docker-machine env $$region) && \
		docker rm -f $(SERVICE_NAME) && docker rm -f $(RABBIT_NAME); \
	done

run-rabbit:
	docker run -d -p 15682:15672 --hostname rabbit \
	-e RABBITMQ_ERLANG_COOKIE='24261958953861120' \
	--name $(RABBIT_NAME) $(RABBIT_NAME):$(TAG)

run-app:
	docker run -d -p 8090:8000 \
	--link rabbit:$(RABBIT_NAME) -e RABBIT_HOST="rabbit" \
	-e RABBIT_PORT="5672" -e RABBIT_MANAGEMENT_PORT="15672" \
	--name $(SERVICE_NAME) $(SERVICE_NAME):$(TAG)
