from nameko.extensions import DependencyProvider


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
