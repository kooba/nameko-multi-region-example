# Nameko Multi Region Messaging Example

Distributed systems are often hosted in geographically dispersed data centers.

This repository contains example showing how messaging between services
in different regions can be accomplished with the help of Nameko framework.

## Use Cases

Three different use cases will show how messages can be distributed
between three different regions.

*Events:* Dispatch events by a service in one region and handle
them by services in all regions. 

*Message processing in master region:* Send message from a service in any
region and process it by service in only one region.

*Asynchronous two-way messaging:* Send a message to specific region and
receive reply back in originating region.

## Setup

To simulate multi-region deployment, create three
hosts: Europe, Asia and America. Each one will be running Docker engine,
with RabbitMQ and example Nameko service in Docker containers.

Ensure Docker, Docker Machine, Docker Compose and
VirtualBox are installed and running:


```sh
$ docker -v && docker-machine -v && docker-compose -v && VBoxManage -v

Docker version 17.03.0-ce, build 60ccb22
docker-machine version 0.10.0, build 76ed2a6
docker-compose version 1.11.2, build dfed245
5.1.18r114002
```

Clone example repository

```sh
$ git clone https://github.com/kooba/nameko-multi-region-example
$ cd nameko-multi-region-example
```

Create three VM machines

`$ make create-machines`

This will take a while, you might want to take a coffee break ☕️

Once it’s done verify your machines are up and running:

```sh
$ docker-machine ls

NAME      ACTIVE   DRIVER       STATE     URL
america   *        virtualbox   Running   tcp://192.168.99.102:2376
asia      -        virtualbox   Running   tcp://192.168.99.100:2376
europe    -        virtualbox   Running   tcp://192.168.99.101:2376
```

Deploy RabbitMQ and Nameko sample service to each of the hosts.
This step will also setup three way federation between Rabbit nodes.

`$ make deploy`

In this step all required Docker images will be downloaded from Docker Hub.
You can create your own local images by calling $ make build-all.
You will have to change docker-compose file to use them.

## Events

```sh
# Get IP for one of our nodes
$ docker-machine ip europe
192.168.99.100

# Try to get non existing product
$ curl 192.168.99.100:8000/products/1
{"message": "Product not found", "error": "NOT_FOUND"}

# Add product
$ curl -XPOST 192.168.99.100:8000/products \
  -d '{"price": "100.00", "name": "Tesla", "id": 1, "quantity": 100}'

# Try to get product again
$ curl 192.168.99.100:8000/products/1
{"name": "Tesla", "quantity": 100, "price": "100.00", "id": 1}

# Now try to get the same product from other regions
$ docker-machine ip asia
192.168.99.101

$ curl 192.168.99.1001:8000/products/1
{"name": "Tesla", "quantity": 100, "price": "100.00", "id": 1}

$ docker-machine ip america
192.168.99.102

$ curl 192.168.99.1002:8000/products/1
{"name": "Tesla", "quantity": 100, "price": "100.00", "id": 1}
```

## Message processing in master region

```sh
# Get IP for our master nodes
$ docker-machine ip europe
192.168.99.100

# Ensure we already have a product from previous example
$ curl 192.168.99.100:8000/products/1
{"name": "Tesla", "quantity": 100, "price": "100.00", "id": 1}

# Let's order our brand new shiny Tesla because why not!

$ curl -XPOST 192.168.99.100:8000/orders \
  -d '{"product_id": 1, "quantity": 1}'

# Verify message was handled in `europe` region only
$ docker-machine ssh europe
$ docker logs nameko-multi-region-example-products
# Look for log in stdout:
Consuming order

$ docker-machine ssh asia
$ docker logs nameko-multi-region-example-products

# `Consuming order` was not logged, message was only processed in `europe` region.
```

## Asynchronous two-way messaging

```sh
# Get IP for our master nodes
$ docker-machine ip europe
192.168.99.100

# Request tax calculation on america
$ curl -XPOST 192.168.99.100:8000/tax/america

# Let's verify calculation response came back
$ docker-machine ssh europe
$ docker logs nameko-multi-region-example-products

# You should see a message logged by `consume_tax_calculation`
{
  'result': {
    'tax': 'You do not owe taxes in region america for order id 1'
   },
   'error': None
}
```
