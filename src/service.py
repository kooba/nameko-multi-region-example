import json
import logging

from marshmallow import ValidationError
from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.extensions import DependencyProvider
from nameko.messaging import Publisher, consume
from nameko.web.handlers import http

from .messaging import (
    consume_and_reply, consume_reply, order_queue,
    orders_exchange, ROUTING_KEY_CALCULATE_TAXES,
    ROUTING_KEY_CALCULATE_TAXES_REPLY, ROUTING_KEY_ORDER_PRODUCT
)
from .models import Order, Product

CACHE = {}


class Cache(DependencyProvider):

    class CacheApi:
        def __init__(self, cache):
            self.cache = cache

        def update(self, key, value):
            self.cache[key] = value

        def get(self, key):
            return self.cache.get(key)

    def get_dependency(self, worker_ctx):
        return self.CacheApi(CACHE)


class Config(DependencyProvider):
    def get_dependency(self, worker_ctx):
        return self.container.config.copy()


class ProductsService:
    name = 'products'

    cache = Cache()
    config = Config()
    dispatch = EventDispatcher()
    order_product_publisher = Publisher(queue=order_queue)
    calculate_taxes_publisher = Publisher(exchange=orders_exchange)

    @http('GET', '/products/<int:product_id>')
    def get_product(self, request, product_id):
        """ Get product from local cache
        """
        product = self.cache.get(product_id)
        if not product:
            return 404, json.dumps({
                'error': 'NOT_FOUND',
                'message': 'Product not found'
            })
        return Product(strict=True).dumps(self.cache.get(product_id)).data

    @http('POST', '/products')
    def add_product(self, request):
        """ Add product to cache in every region

        This endpoint can be called in any region and will dispatch event
        which will be handled by indexer's `handle_product_add` in all regions
        """
        try:
            payload = Product(strict=True).loads(
                request.get_data(as_text=True)
            ).data
        except ValidationError as err:
            return 400, json.dumps({
                'error': 'BAD_REQUEST',
                'message': err.messages
            })
        self.dispatch('product_add', Product(strict=True).dump(payload).data)
        return 200, ''

    @http('POST', '/orders')
    def order_product(self, request):
        """ HTTP entrypoint for ordering products

        This entrypoint can be called in any region but message will be
        published on a federated `fed.order_product` queue that is only
        consumed in `europe` region where master database and service with
        write permissions to it lives.
        """
        try:
            payload = Order(strict=True).loads(
                request.get_data(as_text=True)
            ).data
        except ValidationError as err:
            return 400, json.dumps({
                'error': 'BAD_REQUEST',
                'message': err.messages
            })

        self.order_product_publisher(
            payload, routing_key=ROUTING_KEY_ORDER_PRODUCT
        )
        return 200, ''

    @consume(queue=order_queue)
    def consume_order(self, payload):
        """ Consumes order payloads

        For our example, this consumer is only enabled in `europe` region.
        `asia` and `america` regions have this consumer disabled by setting
        `ENTRYPOINT_BLACKLIST` config value to `consume_order`.
        Custom implementation of ServiceContainer (container.py) uses this
        value to blacklist specific entrypoints.
        """
        logging.info("Consuming order")
        product = self.cache.get(payload['product_id'])
        product['quantity'] -= payload['quantity']

        # Write to master database here...

        self.dispatch(
            'product_update', Product(strict=True).dump(product).data
        )

    @http('POST', '/tax/<string:region>')
    def calculate_tax(self, request, region):

        this_regions = self.config['REGION']

        self.calculate_taxes_publisher(
            {},
            routing_key="{}_{}".format(region, ROUTING_KEY_CALCULATE_TAXES),
            reply_to="{}_{}".format(
                this_regions, ROUTING_KEY_CALCULATE_TAXES_REPLY
            )
        )
        return 200, ''

    @consume_reply()
    def record_tax_calculation(self, payload):
        logging.info(payload)


class IndexerService:
    name = 'indexer'

    cache = Cache()

    @event_handler(
        'products', 'product_add',
        handler_type=BROADCAST, reliable_delivery=False
    )
    def handle_product_add(self, payload):
        logging.info("Handling product add: {}".format(payload))
        payload = Product(strict=True).load(payload).data
        self.cache.update(
            payload['id'],
            payload
        )

    @event_handler(
        'products', 'product_update',
        handler_type=BROADCAST, reliable_delivery=False
    )
    def handle_product_update(self, payload):
        logging.info("Handling product update: {}".format(payload))
        payload = Product(strict=True).load(payload).data
        product = self.cache.get(payload['id'])
        product.update(payload)
        self.cache.update(
            payload['id'],
            payload
        )


class TaxesService:
    name = 'taxes'

    config = Config()

    @consume_and_reply()
    def calculate_taxes(self, payload):
        this_region = self.config['REGION']
        logging.info("Received request in {}".format(this_region))
        return {
            'tax': 'You do not owe taxes in region {}'.format(this_region)
        }
