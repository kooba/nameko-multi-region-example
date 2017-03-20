import json

from marshmallow import ValidationError
from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.extensions import DependencyProvider
from nameko.web.handlers import http

from .models import Product, ProductBase

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


class ProductsService:
    name = 'products'

    cache = Cache()
    dispatch = EventDispatcher()

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

    @http('PUT', '/products/<int:product_id>')
    def update_product(self, request, product_id):
        try:
            payload = ProductBase(strict=True).loads(
                request.get_data(as_text=True)
            ).data
        except ValidationError as err:
            return 400, json.dumps({
                'error': 'BAD_REQUEST',
                'message': err.messages
            })
        payload['id'] = product_id
        self.dispatch(
            'product_update', Product(strict=True).dump(payload).data
        )
        return 200, ''


class IndexerService:
    name = 'indexer_service'

    cache = Cache()

    @event_handler(
        'products', 'product_update',
        handler_type=BROADCAST, reliable_delivery=False
    )
    @event_handler(
        'products', 'product_add',
        handler_type=BROADCAST, reliable_delivery=False
    )
    def handle_product_update(self, payload):
        print("Received {}".format(payload))
        payload = Product(strict=True).load(payload).data
        self.cache.update(
            payload['id'],
            payload
        )
