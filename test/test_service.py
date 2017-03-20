import json
import pytest

from mock import call, patch
from nameko.standalone.events import event_dispatcher
from nameko.testing.services import entrypoint_waiter

from src.service import CACHE


@pytest.fixture
def data():
    with patch.dict(CACHE):
        CACHE[1] = {
            'id': 1,
            'name': "Tesla",
            'price': 100.00
        }
        yield


class TestProductService:

    def test_will_get_product(self, products_service, web_session, data):
        response = web_session.get('/products/1')
        assert response.status_code == 200
        assert response.json() == {'price': '100.0', 'name': 'Tesla', 'id': 1}

    def test_product_not_found(self, products_service, web_session):
        response = web_session.get('/products/1')
        assert response.status_code == 404
        assert response.json() == {
            'error': 'NOT_FOUND',
            'message': 'Product not found'
        }

    def test_will_add_product(self, products_service, web_session):
        payload = {'price': '100.0', 'name': 'Tesla', 'id': 1}
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
                'id': ['Missing data for required field.']
            }
        }

    def test_will_update_product(self, products_service, web_session, data):
        payload = {'price': '200.0', 'name': 'Tesla'}
        response = web_session.put('/products/1', data=json.dumps(payload))
        assert response.status_code == 200

        payload['id'] = 1
        assert products_service.dispatch.call_args_list == [
            call('product_update', payload)
        ]

    def test_will_fail_updating_product(self, products_service, web_session):
        payload = {'price': 'foo'}
        response = web_session.put('/products/1', data=json.dumps(payload))
        assert response.status_code == 400
        assert response.json() == {
            'error': 'BAD_REQUEST',
            'message': {
                'price': ['Not a valid number.']
            }
        }


class TestIndexerService:

    def test_will_update_cache(self, indexer_service, config, data):
        original_price = CACHE[1]['price']

        payload = {'price': '101.0', 'name': 'Tesla', 'id': 1}

        container = indexer_service.container
        dispatch = event_dispatcher(config)

        with entrypoint_waiter(container, 'handle_product_update'):
            dispatch('products', 'product_update', payload)
        assert CACHE[1]['price'] > original_price

