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

## Setup 2 VB hosts - In progress

Setup 2 VM docker machines representing different regions

```sh
$ docker-machine create --driver virtualbox europe
$ docker-machine create --driver virtualbox asia
```

Switch to particular docker:

`$ eval $(docker-machine env europe)`

Deploy Rabbit on each host

`$ make rabbit`


3 - Enable federation / Use rabbit configuration?
4 - Deploy Service Image to both hosts:
    user docker compose to do it?
    will have to pass different parameters when running docker compose
5 - Test
