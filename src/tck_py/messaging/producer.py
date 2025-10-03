# src/tck_py/messaging/producer.py
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from tck_py.shared.exceptions import PublishError


@pytest.mark.asyncio
class BaseTestProducerContract:
    """
    TCK Contract: Defines the compliance test suite for any provider
    implementing the ProducerProtocol.
    This contract requires a more complex fixture to allow for message
    consumption and verification.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[tuple[Any, Callable]]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function. This factory, when awaited,
        must return a tuple containing two items:

        1. An initialized producer instance to be tested.
        2. A helper async function `get_message_from_topic(topic: str, timeout: float)`
           which consumes and returns a single message from the specified topic,
           or None if the timeout is reached. The returned message object should
           have attributes like `payload`, `key`, and `headers`.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_publish_simple_message(self, provider_factory):
        """
        Verifies that a simple binary payload can be published and consumed.
        """
        producer, get_message_from_topic = await provider_factory()
        topic = f"tck-producer-test-{uuid.uuid4()}"
        payload = b"hello world"

        await producer.publish(topic=topic, payload=payload)

        consumed_message = await get_message_from_topic(topic, timeout=2.0)

        assert consumed_message is not None
        assert consumed_message.payload == payload

    async def test_publish_with_key(self, provider_factory):
        """
        Verifies that a message published with a key is consumed with that key.
        """
        producer, get_message_from_topic = await provider_factory()
        topic = f"tck-producer-test-{uuid.uuid4()}"
        payload = b"message with key"
        key = f"partition-key-{uuid.uuid4()}"

        await producer.publish(topic=topic, payload=payload, key=key)

        consumed_message = await get_message_from_topic(topic, timeout=2.0)

        assert consumed_message is not None
        assert consumed_message.key == key
        assert consumed_message.payload == payload

    async def test_publish_with_headers(self, provider_factory):
        """
        Verifies that a message published with headers is consumed with those headers.
        """
        producer, get_message_from_topic = await provider_factory()
        topic = f"tck-producer-test-{uuid.uuid4()}"
        payload = b"message with headers"
        headers = {"x-trace-id": str(uuid.uuid4()), "x-message-type": "test-event"}

        await producer.publish(topic=topic, payload=payload, headers=headers)

        consumed_message = await get_message_from_topic(topic, timeout=2.0)

        assert consumed_message is not None
        # Headers might be encoded as bytes,
        # so we check for inclusion and decode if needed.
        for key, value in headers.items():
            assert key in consumed_message.headers
            header_value = consumed_message.headers[key]
            if isinstance(header_value, bytes):
                header_value = header_value.decode("utf-8")
            assert header_value == value

    async def test_publish_to_unavailable_broker_raises_exception(
        self, provider_factory
    ):
        """
        Verifies that attempting to publish when the message broker is unavailable
        raises a standardized PublishError.
        """
        # This test requires the factory to be configured with a bad address
        unavailable_config = {"bootstrap_servers": "localhost:9999"}
        producer, _ = await provider_factory(config=unavailable_config)
        topic = f"tck-producer-test-{uuid.uuid4()}"
        payload = b"this will fail"

        with pytest.raises(PublishError):
            # Some producers might not fail on publish but on connect/init.
            # A robust test should handle both. Here we test the publish call.
            await producer.publish(topic=topic, payload=payload)
