"""Nameko service for multi-region example
"""

from datetime import datetime
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

class TimeService:
    """Nameko Service: products"""
    name = 'time'

    cache = Cache()
    dispatch = EventDispatcher()

    @http('GET', '/time')
    def get_time(self, request):
        return json.dumps({'time': self.cache.get('time')})

    @http('PUT', '/time')
    def update_time(self, request):
        payload = {'time': datetime.now().isoformat()}
        self.dispatch("time_refresh", payload)
        return json.dumps({'payload': payload})


class IndexerService:
    name = 'indexer'

    cache = Cache()

    @event_handler(
        "time", "time_refresh", handler_type=BROADCAST, reliable_delivery=False
    )
    def handle_time_update(self, payload):
        print("Received {}".format(payload))
        self.cache.update('time', payload['time'])
