import json
import pytest
from src.service import ProductsService


@pytest.fixture
def config(rabbit_config, web_config):
    config = rabbit_config.copy()
    config.update(web_config)
    return config


@pytest.fixture
def service_container(config, container_factory):
    container = container_factory(ProductsService, config)
    container.start()
    return container


def test_will_update_product(service_container, web_session):
    payload = {
        'stock_quantity': 10
    }
    product_id = 1
    response = web_session.put(
        '/products/{}'.format(product_id), json.dumps(payload))
    results = response.json()
    assert response.status_code == 200
    expected_payload = payload.copy()
    expected_payload['product_id'] = product_id
    assert results == {'product': expected_payload}
