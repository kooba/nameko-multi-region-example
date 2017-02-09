import json

from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.extensions import DependencyProvider
from nameko.web.handlers import http

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
    name = 'products_service'

    cache = Cache()
    dispatch = EventDispatcher()

    @http('GET', '/products/<int:product_id>')
    def get_time(self, request, product_id):
        return json.dumps(
            {'product': self.cache.get('product_{}'.format(product_id))})

    @http('PUT', '/products/<int:product_id>')
    def update_time(self, request, product_id):
        request_data = request.get_data(as_text=True)
        payload = json.loads(request_data)
        payload['product_id'] = product_id
        self.dispatch("product_update", payload)
        return json.dumps({'product': payload})


class IndexerService:
    name = 'indexer_service'

    cache = Cache()

    @event_handler(
        "products_service", "product_update",
        handler_type=BROADCAST, reliable_delivery=False
    )
    def handle_product_update(self, payload):
        print("Received {}".format(payload))
        self.cache.update('product_{}'.format(payload['product_id']), payload)
