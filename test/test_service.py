import json
import pytest

from mock import call, patch
from nameko.exceptions import ExtensionNotFound
from nameko.standalone.events import event_dispatcher
from nameko.testing.services import entrypoint_waiter, entrypoint_hook

from src.dependencies import CACHE
from src.messaging import (
    ROUTING_KEY_CALCULATE_TAXES, ROUTING_KEY_CALCULATE_TAXES_REPLY,
    ROUTING_KEY_ORDER_PRODUCT, orders_exchange
)
from src.service import ProductsService


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
            call('product_added', payload)
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

    def test_will_fail_ordering_product(self, products_service, web_session):
        payload = {}
        response = web_session.post('/orders', data=json.dumps(payload))
        assert response.status_code == 400
        assert response.json() == {
            'message': {
                'quantity': ['Missing data for required field.'],
                'product_id': ['Missing data for required field.']
            },
            'error': 'BAD_REQUEST'
        }
        assert not products_service.order_product_publisher.called

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

    def test_will_request_tax_calculation(
        self, products_service, web_session, config
    ):
        this_region = config['REGION']
        tax_region = 'asia'
        response = web_session.post('/tax/{}'.format(tax_region))
        assert response.status_code == 200
        assert [
            call(
                {'order_id': 1},
                reply_to='{}_calculate_taxes_reply'.format(this_region),
                routing_key='{}_calculate_taxes'.format(tax_region)
            )
        ] == products_service.calculate_taxes_publisher.call_args_list

    def test_will_consume_tax_calculation_results(
        self, products_service, publish, config
    ):
        payload = {'order_id': 1}

        with patch('src.service.logging') as logging:
            with entrypoint_waiter(
                products_service.container, 'consume_tax_calculation'
            ):
                publish(
                    payload,
                    '{}_{}'.format(
                        config['REGION'], ROUTING_KEY_CALCULATE_TAXES_REPLY
                    ),
                    exchange=orders_exchange
                )
        assert logging.info.call_args_list == [call(payload)]


class TestIndexerService:

    def test_will_add_product_to_cache(self, indexer_service, config):
        payload = {'price': 101.0, 'name': 'Tesla', 'id': 1, 'quantity': 100}

        container = indexer_service.container
        dispatch = event_dispatcher(config)

        with entrypoint_waiter(container, 'handle_product_added'):
            dispatch('products', 'product_added', payload)
        assert CACHE[payload['id']] == payload


class TestTaxesService:

    def test_will_calculate_taxes(self, taxes_service, publish, config):
        payload = {'order_id': 1}
        region = config['REGION']
        with entrypoint_waiter(
            taxes_service.container, 'calculate_taxes'
        ) as results:
            publish(
                payload,
                '{}_{}'.format(region, ROUTING_KEY_CALCULATE_TAXES),
                exchange=orders_exchange
            )
        assert results.get() == {
            'tax': 'You do not owe taxes in region {} for order id {}'.format(
                region, payload['order_id']
            )
        }

    def test_will_fail_calculating_taxes(self, taxes_service, publish, config):
        payload = {}
        region = config['REGION']
        with entrypoint_waiter(
            taxes_service.container, 'calculate_taxes'
        ) as results:
            publish(
                payload,
                '{}_{}'.format(region, ROUTING_KEY_CALCULATE_TAXES),
                exchange=orders_exchange
            )
        assert results.exc_info == {
            'exc_path': 'marshmallow.exceptions.ValidationError',
            'value': "{'order_id': ['Missing data for required field.']}",
            'exc_args': [{
                'order_id': ['Missing data for required field.']
            }],
            'exc_type': 'ValidationError'
        }
