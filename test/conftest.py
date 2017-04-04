import os
import yaml

import pytest
from collections import namedtuple

from kombu import Connection
from kombu.pools import connections as kombu_connections
from kombu.pools import producers
from nameko.cli.main import setup_yaml_parser
from nameko.constants import AMQP_URI_CONFIG_KEY
from nameko.testing.services import replace_dependencies

from src.messaging import orders_exchange
from src.service import IndexerService, ProductsService, TaxesService


@pytest.fixture(scope="session")
def project_root():
    return os.path.dirname(os.path.dirname(__file__))


@pytest.fixture(scope="module")
def test_config(project_root):
    config_file = os.path.join(project_root, "config.yml")
    setup_yaml_parser()
    with open(config_file) as stream:
        config = yaml.load(stream.read())
    return config


@pytest.fixture
def config(test_config, rabbit_config, web_config):
    config = test_config.copy()
    config.update(web_config)
    config.update(rabbit_config)
    return config


@pytest.fixture
def create_service_meta(container_factory, config):

    def create(service_cls, *dependencies, **dependency_map):
        """ Create service instance with specified dependencies mocked
        """
        dependency_names = list(dependencies) + list(dependency_map.keys())

        ServiceMeta = namedtuple(
            'ServiceMeta', ['container'] + dependency_names
        )
        container = container_factory(service_cls, config)

        mocked_dependencies = replace_dependencies(
            container, *dependencies, **dependency_map
        )
        if len(dependency_names) == 1:
            mocked_dependencies = (mocked_dependencies, )

        container.start()

        return ServiceMeta(container, *mocked_dependencies, **dependency_map)

    return create


@pytest.fixture
def products_service(create_service_meta):
    return create_service_meta(
        ProductsService, 'dispatch', 'order_product_publisher',
        'calculate_taxes_publisher'
    )


@pytest.fixture
def indexer_service(create_service_meta):
    return create_service_meta(IndexerService)


@pytest.fixture
def taxes_service(create_service_meta):
    return create_service_meta(TaxesService)


@pytest.fixture
def publish(config):
    conn = Connection(config[AMQP_URI_CONFIG_KEY])

    def publish(payload, routing_key, exchange=None, **kwargs):
        """Publish an AMQP message."""
        with kombu_connections[conn].acquire(block=True) as connection:
            if exchange is not None:
                exchange.maybe_bind(connection)
            with producers[conn].acquire(block=True) as producer:
                producer.publish(
                    payload,
                    exchange=exchange,
                    serializer='json',
                    routing_key=routing_key,
                    **kwargs)

    return publish


@pytest.fixture(autouse=True)
def commute_exchange():
    """Ensure exchanges are not bound to channels from previous test runs.

    This fixtures is temporary and should be removed once changes from
    https://github.com/mattbennett/nameko/pull/7/files land in nameko
    codebase and frontend_facade.publishers.Publisher is updated
    """
    yield
    orders_exchange._channel = None
