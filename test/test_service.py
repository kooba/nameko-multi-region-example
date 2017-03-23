import json
import pytest

from mock import call, patch
from nameko.exceptions import ExtensionNotFound
from nameko.standalone.events import event_dispatcher
from nameko.testing.services import entrypoint_waiter, entrypoint_hook

from src.service import (
    CACHE, ROUTING_KEY_ORDER_PRODUCT, orders_exchange, ProductsService
)


@pytest.fixture
def data():
    with patch.dict(CACHE):
        CACHE[1] = {
            'id': 1,
            'name': "Tesla",
            'price': 100.00,
            'quantity': 100
        }
        yield


class TestProductService:

    def test_will_get_product(self, products_service, web_session, data):
        response = web_session.get('/products/1')
        assert response.status_code == 200
        assert response.json() == {
            'price': '100.0', 'name': 'Tesla', 'id': 1, 'quantity': 100
        }

    def test_product_not_found(self, products_service, web_session):
        response = web_session.get('/products/1')
        assert response.status_code == 404
        assert response.json() == {
            'error': 'NOT_FOUND',
            'message': 'Product not found'
        }

    def test_will_add_product(self, products_service, web_session):
        payload = {'price': '100.0', 'name': 'Tesla', 'id': 1, 'quantity': 100}
        response = web_session.post('/products', data=json.dumps(payload))
        assert response.status_code == 200
        assert products_service.dispatch.call_args_list == [
            call('product_add', payload)
        ]

    def test_fail_adding_product(self, products_service, web_session):
        payload = {}
        response = web_session.post('/products', data=json.dumps(payload))
        assert response.status_code == 400
        assert response.json() == {
            'error': 'BAD_REQUEST',
            'message': {
                'id': ['Missing data for required field.'],
                'name': ['Missing data for required field.'],
                'price': ['Missing data for required field.'],
                'quantity': ['Missing data for required field.']
            }
        }

    def test_will_order_product(self, products_service, web_session):
        payload = {'product_id': 1, 'quantity': 1}
        response = web_session.post('/orders', data=json.dumps(payload))
        assert response.status_code == 200
        assert [call(
            {'quantity': 1, 'product_id': 1},
            routing_key=ROUTING_KEY_ORDER_PRODUCT
        )] == products_service.order_product_publisher.call_args_list

    def test_will_consume_order(self, products_service, publish, data):
        payload = {'quantity': 1, 'product_id': 1}
        with entrypoint_waiter(
            products_service.container, 'consume_order'
        ):
            publish(
                payload, ROUTING_KEY_ORDER_PRODUCT,
                exchange=orders_exchange
            )
        assert products_service.dispatch.call_args_list == [
            call(
                'product_update',
                {'quantity': 99, 'id': 1, 'name': 'Tesla', 'price': '100.0'}
            )
        ]

    def test_can_blacklist_consumer(self, container_factory, config):

        config['ENTRYPOINT_BLACKLIST'] = ['consume_order']

        container = container_factory(ProductsService, config)
        container.start()

        with pytest.raises(ExtensionNotFound) as exc_info:
            with entrypoint_hook(container, 'consume_order'):
                pass
        assert "No entrypoint for 'consume_order' found" in str(exc_info.value)


class TestIndexerService:

    def test_will_add_product_to_cache(self, indexer_service, config):
        payload = {'price': 101.0, 'name': 'Tesla', 'id': 1, 'quantity': 100}

        container = indexer_service.container
        dispatch = event_dispatcher(config)

        with entrypoint_waiter(container, 'handle_product_add'):
            dispatch('products', 'product_add', payload)
        assert CACHE[payload['id']] == payload

    def test_will_update_cache(self, indexer_service, config, data):
        payload = {'price': 101.0, 'name': 'Tesla', 'id': 1, 'quantity': 100}

        container = indexer_service.container
        dispatch = event_dispatcher(config)

        with entrypoint_waiter(container, 'handle_product_update'):
            dispatch('products', 'product_update', payload)
        assert CACHE[payload['id']] == payload


