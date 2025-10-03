# tests/reference/messaging/test_in_memory_messaging.py
import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.messaging.consumer import BaseTestConsumerContract, ProcessingOutcome
from tck_py.messaging.producer import BaseTestProducerContract
from tck_py.shared.exceptions import PublishError
from tck_py.shared.models import ConsumedMessage

# =============================================================================
# 1. IN-MEMORY BROKER SIMULATION
# =============================================================================


class InMemoryBroker:
    """A simple asyncio-based broker to simulate a message bus."""

    def __init__(self):
        self._topics: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def publish(self, topic: str, message: ConsumedMessage):
        await self._topics[topic].put(message)

    async def get_message(self, topic: str) -> ConsumedMessage | None:
        try:
            return await asyncio.wait_for(self._topics[topic].get(), timeout=2.0)
        except TimeoutError:
            return None


# =============================================================================
# 2. PROVIDER IMPLEMENTATION (Refactored to single responsibilities)
# =============================================================================


class InMemoryProducer:
    """In-memory implementation for the Producer protocol."""

    def __init__(self, broker: InMemoryBroker, config: dict | None = None):
        self._broker = broker
        # Simulate connection failure based on bad config
        self._should_fail = (
            "localhost:9999" in config.get("bootstrap_servers", "") if config else False
        )

    async def publish(
        self,
        topic: str,
        payload: bytes,
        key: str | None = None,
        headers: dict | None = None,
    ):
        if self._should_fail:
            raise PublishError("Broker unavailable")

        message = ConsumedMessage(payload=payload, key=key, headers=headers or {})
        await self._broker.publish(topic, message)


class InMemoryConsumer:
    """In-memory implementation for the Consumer protocol."""

    def __init__(self, broker: InMemoryBroker):
        self._broker = broker

    # We remove the config logic here to simplify the class (SRP)
    # and delegate retry/DLQ logic to the `run_consumer_loop` parameters.

    async def run_consumer_loop(self, topic: str, handler: Callable, config: dict):
        max_attempts = config.get("max_attempts", 3)
        dlq_topic = "tck_dlq"

        while True:
            # We use a non-blocking get here as a simple loop check
            # NOTE: Consumer contract expects a fast exit if the test ends.
            message = await self._broker.get_message(topic)
            if not message:
                await asyncio.sleep(0)
                continue

            attempts = 0
            outcome = ProcessingOutcome.RETRY

            while attempts < max_attempts:
                attempts += 1
                outcome = await handler(message)
                if outcome == ProcessingOutcome.SUCCESS:
                    break  # Acknowledge and move to next message

            # For in-memory, RETRY and FAIL have similar effects:
            # we try again immediately.
            if attempts >= max_attempts and outcome != ProcessingOutcome.SUCCESS:
                # Move to DLQ
                await self._broker.publish(
                    topic=dlq_topic,
                    message=ConsumedMessage(
                        payload=message.payload,
                        key=message.key,
                        headers=message.headers,
                    ),
                )


# =============================================================================
# 3. TCK COMPLIANCE TESTS (Refactored to SRP)
# =============================================================================


# Use a module-level fixture for the broker to allow communication between
# the producer and consumer tests in the same file.
@pytest.fixture(scope="module")
def shared_broker():
    return InMemoryBroker()


class TestInMemoryProducerCompliance(BaseTestProducerContract):
    """Runs the Producer TCK compliance suite against the InMemoryProducer."""

    @pytest.fixture
    def provider_factory(
        self, shared_broker
    ) -> Callable[..., Awaitable[tuple[Any, Callable]]]:
        """
        Factory for the Producer TCK.
        Returns: (producer_instance, get_message_from_topic)
        """

        async def _factory(config: dict | None = None):
            producer = InMemoryProducer(broker=shared_broker, config=config)

            async def get_message_from_topic_prod(topic: str, timeout: float):
                # The broker is used as the consumer for verification
                # We use the broker's get_message which already respects
                # its internal timeout (2.0s)
                # The explicit timeout argument from the TCK is ignored
                # here as the broker is a simple mock.
                return await shared_broker.get_message(topic)

            return producer, get_message_from_topic_prod

        return _factory


class TestInMemoryConsumerCompliance(BaseTestConsumerContract):
    """Runs the Consumer TCK compliance suite against the InMemoryConsumer."""

    @pytest.fixture
    def provider_factory(
        self, shared_broker
    ) -> Callable[..., Awaitable[tuple[Any, Callable, Callable]]]:
        """
        Factory for the Consumer TCK.
        Returns: (consumer_task, publish_func, get_message_from_dlq)
        """

        async def _factory(handler=None, topic=None, consumer_config=None, config=None):
            consumer = InMemoryConsumer(broker=shared_broker)

            consumer_task = asyncio.create_task(
                consumer.run_consumer_loop(topic, handler, consumer_config)
            )

            async def publish_func(payload, key=None, headers=None):
                producer = InMemoryProducer(broker=shared_broker)
                await producer.publish(topic, payload, key, headers)

            async def get_message_from_dlq(timeout: float):
                # The DLQ verification relies on the broker to deliver the message
                return await shared_broker.get_message("tck_dlq")

            return consumer_task, publish_func, get_message_from_dlq

        return _factory
