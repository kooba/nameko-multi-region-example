import json
import pytest
from mock import call, patch
from src.service import ProductsService, CACHE


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

    def test_will_get_product(self, service, web_session, data):
        response = web_session.get('/products/1')
        assert response.status_code == 200
        assert response.json() == {'price': '100.0', 'name': 'Tesla', 'id': 1}

    def test_product_not_found(self, service, web_session):
        response = web_session.get('/products/1')
        assert response.status_code == 404
        assert response.json() == {
            'error': 'NOT_FOUND',
            'message': 'Product not found'
        }

    def test_will_add_product(self, service, web_session):
        payload = {
                'price': '100.0',
                'name': 'Tesla',
                'id': 1
            }
        response = web_session.post('/products', data=json.dumps(payload))
        assert response.status_code == 200
        assert service.dispatch.call_args_list == [
            call('product_add', payload)
        ]

    def test_fail_adding_product(self, service, web_session):
        payload = {}
        response = web_session.post('/products', data=json.dumps(payload))
        assert response.status_code == 400
        assert response.json() == {
            'error': 'BAD_REQUEST',
            'message': {
                'id': ['Missing data for required field.']
            }
        }
    # def test_will_update_product
    # def will_fail_updating_product


def test_will_update_product(service, web_session):
    payload = {
        'price': '200.00'
    }
    product_id = 1
    response = web_session.put(
        '/products/{}'.format(product_id), data=json.dumps(payload)
    )
    results = response.json()
    assert response.status_code == 200
    expected_payload = payload.copy()
    expected_payload['product_id'] = product_id
    assert results == {'product': expected_payload}
