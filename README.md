# Nameko Multi Region Messaging Example

### Build Services

```sh
$ make build-all
```

### Run Services

```sh
$ make run-app
```

### Call API

Service is running on port 8090
Initial call to get time will return null

```sh
$ curl 0.0.0.0:8090/time

{"time": null}
```

Update time in cache

```sh
$ curl -XPUT curl 0.0.0.0:8090/time

{"time": "2017-01-13T15:11:14.448717"}
```

Subsequent calls will return the same timestamp

Each time we call update cache event is published and all subscribers receive the message.

# NEXT TODO:

### Setup 2 VB hosts - In progress

Setup 2 VM docker machines representing different regions

```sh
$ docker-machine create --driver virtualbox europe
$ docker-machine create --driver virtualbox asia
```

### Build and deploy Service

Build rabbit with Federation plugin enabled on each host

```sh
# Switch to `europe` host
$ eval $(docker-machine env europe)
# Build rabbitmq and service docker images
$ make build-all
# Run rabbitmq container
$ make rabbit
# Run service container
$ make run-app

# Switch to `asia` host
$ eval $(docker-machine env asia)
# Build rabbitmq and service docker images
$ make build-all
# Run rabbitmq container
$ make rabbit
# Run service container
$ make run-app
```

# TODO for demo build containers and upload them to the docker hub?

### Setup federation

Get IPs for `europe` and `asia` hosts

```sh
$ docker-machine ip europe
192.168.99.102

$ docker-machine ip asia
192.168.99.103
```

Enable upstream federation and add federation policies on both hosts

```sh
$ eval $(docker-machine env europe)

$ docker exec rabbit sh -c "rabbitmqctl set_parameter federation-upstream asia-upstream '{\"uri\":\"amqp://192.168.99.103:5672\"}'"
Setting runtime parameter "asia-upstream" for component "federation-upstream" to "{\"uri\":\"amqp://192.168.99.103:5672\"}" ...

$ docker exec rabbit sh -c "rabbitmqctl set_policy --apply-to queues federate-queues \"^(evt-.*|fed\\..*)$\" '{\"federation-upstream-set\":\"all\"}'"
Setting policy "federate-queues" for pattern "^(evt-.*|fed\\..*)$" to "{\"federation-upstream-set\":\"all\"}" with priority "0" ...


$ eval $(docker-machine env asia)
$ docker exec rabbit sh -c "rabbitmqctl set_parameter federation-upstream asia-upstream '{\"uri\":\"amqp://192.168.99.102:5672\"}'"
Setting runtime parameter "asia-upstream" for component "federation-upstream" to "{\"uri\":\"amqp://192.168.99.102:5672\"}" ...

$ docker exec rabbit sh -c "rabbitmqctl set_policy --apply-to queues federate-queues \"^(evt-.*|fed\\..*)$\" '{\"federation-upstream-set\":\"all\"}'"
Setting policy "federate-queues" for pattern "^(evt-.*|fed\\..*)$" to "{\"federation-upstream-set\":\"all\"}" with priority "0" ...
```

# Tunnel Rabbit Management Consoles

```sh
$ docker-machine ssh europe -L 55672:localhost:15672
$ docker-machine ssh asia -L 56672:localhost:15672
```


3 - Enable federation / Use rabbit configuration?
4 - Deploy Service Image to both hosts:
    user docker compose to do it?
    will have to pass different parameters when running docker compose
5 - Test
