import kombu.serialization
from kombu import Queue
from kombu.common import maybe_declare
from nameko.amqp import get_connection, get_producer
from nameko.constants import AMQP_URI_CONFIG_KEY, DEFAULT_SERIALIZER
from nameko.exceptions import UnserializableValueError, serialize
from nameko.messaging import Consumer as NamekoConsumer

from .service import (
    orders_exchange, ROUTING_KEY_CALCULATE_TAXES,
    ROUTING_KEY_CALCULATE_TAXES_REPLY
)

REGIONS = ['europe', 'asia', 'america']

queue_calculate_taxes = Queue(
    exchange=orders_exchange,
    routing_key=ROUTING_KEY_CALCULATE_TAXES,
    name='fed.{}'.format(ROUTING_KEY_CALCULATE_TAXES)
)


class ReplyConsumer(NamekoConsumer):
    def handle_result(self, message, worker_ctx, result=None, exc_info=None):
        result, exc_info = self.send_response(message, result, exc_info)
        self.handle_message_processed(message, result, exc_info)
        return result, exc_info

    def setup(self):
        """Bind reply queues in all regions to `orders` exchange"""
        super(ReplyConsumer, self).setup()
        config = self.container.config

        with get_connection(config[AMQP_URI_CONFIG_KEY]) as conn:

            maybe_declare(orders_exchange, conn)

            for region in REGIONS:
                maybe_declare(Queue(
                    exchange=orders_exchange,
                    routing_key='{}_{}'.format(
                        region, ROUTING_KEY_CALCULATE_TAXES_REPLY
                    ),
                    name='fed.{}_{}'.format(
                        region, ROUTING_KEY_CALCULATE_TAXES_REPLY
                    )
                ), conn)

    def send_response(self, message, result, exc_info):

        error = None
        if exc_info is not None:
            error = serialize(exc_info[1])

        try:
            kombu.serialization.dumps(result, DEFAULT_SERIALIZER)
        except Exception:
            # `error` below is guaranteed to serialize to json
            error = serialize(UnserializableValueError(result))
            result = None

        config = self.container.config

        with get_producer(config[AMQP_URI_CONFIG_KEY]) as producer:

            routing_key = message.properties.get('reply_to')

            msg = {'result': result, 'error': error}

            producer.publish(
                msg,
                exchange=orders_exchange,
                serializer=DEFAULT_SERIALIZER,
                routing_key=routing_key
            )

        return result, error

consume_and_reply = ReplyConsumer.decorator
