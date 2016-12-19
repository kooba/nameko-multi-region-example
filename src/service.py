"""Nameko service for multi-region example
"""

from datetime import datetime
import json

from nameko.events import EventDispatcher, event_handler, BROADCAST
from nameko.web.handlers import http


class TimeService:
    """Nameko Service: products"""
    name = 'time'

    cache = {}
    dispatch = EventDispatcher()


    @http('GET', '/time')
    def get_time(self, request):
        if not self.cache.get('time'):
            self.cache['time'] = datetime.now().isoformat()
        return json.dumps({'time': self.cache['time']})

    @http('PUT', '/time')
    def update_time(self, request):
        payload = {'time': datetime.now().isoformat()}
        self.dispatch("time_refresh", payload)
        return json.dumps({'payload': payload})

    @event_handler(
        "time", "time_refresh", handler_type=BROADCAST, reliable_delivery=False
    )
    def handle_time_update(self, payload):
        print("Received {}".format(payload))
        self.cache['time'] = payload['time']
