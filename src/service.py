import json

from kombu import Exchange, Queue
from marshmallow import ValidationError
from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.extensions import DependencyProvider
from nameko.messaging import Publisher, consume
from nameko.web.handlers import http

from .models import Order, Product

CACHE = {}

ROUTING_KEY_ORDER_PRODUCT = 'order_product'

orders_exchange = Exchange(name='orders')

order_queue = Queue(
    exchange=orders_exchange,
    routing_key=ROUTING_KEY_ORDER_PRODUCT,
    name='fed.{}'.format(ROUTING_KEY_ORDER_PRODUCT)
)


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


# TODO: Remove
class Config(DependencyProvider):
    def get_dependency(self, worker_ctx):
        return self.container.config.copy()


class ProductsService:
    name = 'products'

    cache = Cache()
    dispatch = EventDispatcher()
    order_product_publisher = Publisher(queue=order_queue)
    config = Config()

    @http('GET', '/products/<int:product_id>')
    def get_product(self, request, product_id):
        product = self.cache.get(product_id)
        if not product:
            return 404, json.dumps({
                'error': 'NOT_FOUND',
                'message': 'Product not found'
            })
        return Product(strict=True).dumps(self.cache.get(product_id)).data

    @http('POST', '/products')
    def add_product(self, request):
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

    # TODO: black list of this endpoint example
    @http('POST', '/orders')
    def order_product(self, request):
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
        print("Consuming order")
        product = self.cache.get(payload['product_id'])
        product['quantity'] -= payload['quantity']

        # TODO: Write to master DB?

        self.dispatch(
            'product_update', Product(strict=True).dump(product).data
        )


class IndexerService:
    name = 'indexer_service'

    cache = Cache()

    @event_handler(
        'products', 'product_add',
        handler_type=BROADCAST, reliable_delivery=False
    )
    def handle_product_add(self, payload):
        print("Handling product add: {}".format(payload))
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
        print("Handling product update: {}".format(payload))
        payload = Product(strict=True).load(payload).data
        product = self.cache.get(payload['id'])
        product.update(payload)
        self.cache.update(
            payload['id'],
            payload
        )
