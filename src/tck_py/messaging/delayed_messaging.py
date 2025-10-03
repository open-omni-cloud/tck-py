# src/tck_py/messaging/delayed_messaging.py
import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable

import pytest


@pytest.mark.asyncio
class BaseTestDelayedMessagingContract:
    """
    TCK Contract: Defines the compliance test suite for delayed messaging.
    """

    @pytest.fixture
    def provider_factory(
        self,
    ) -> Callable[..., Awaitable[tuple[Callable, Callable]]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function. This factory,
        when awaited, must return a tuple containing two items:

        1. A helper async function `publish_func(topic, payload, key,
            headers, delay_seconds)` which sends a delayed message.
        2. A helper async function `get_message_from_topic(topic)`
           which consumes and returns a single message from the
           specified topic.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    async def test_message_is_delivered_after_delay(self, provider_factory):
        """
        Verifies that a message with a delay is consumed only after
        the delay has passed.
        """
        publish, get_message_from_topic = provider_factory
        destination_topic = f"tck-delayed-test-{uuid.uuid4()}"
        payload = b"this message is fashionably late"
        delay_seconds = 2.0

        start_time = time.monotonic()
        await publish(
            topic=destination_topic, payload=payload, delay_seconds=delay_seconds
        )

        TIMEOUT = 3.0
        try:
            consumed_message = await asyncio.wait_for(
                get_message_from_topic(destination_topic), timeout=TIMEOUT
            )
        except TimeoutError:
            pytest.fail(f"Message not delivered to topic in {TIMEOUT}s.")

        end_time = time.monotonic()

        elapsed = end_time - start_time

        assert consumed_message is not None
        assert consumed_message.payload == payload
        assert elapsed >= delay_seconds
        assert elapsed < delay_seconds + 1.0

    async def test_message_without_delay_is_delivered_immediately(
        self, provider_factory
    ):
        """
        Verifies that a message with no delay is delivered almost instantly.
        """
        publish, get_message_from_topic = provider_factory
        destination_topic = f"tck-delayed-test-{uuid.uuid4()}"
        payload = b"this message is on time"

        start_time = time.monotonic()
        await publish(topic=destination_topic, payload=payload, delay_seconds=None)

        TIMEOUT = 2.0
        try:
            consumed_message = await asyncio.wait_for(
                get_message_from_topic(destination_topic), timeout=TIMEOUT
            )
        except TimeoutError:
            pytest.fail(f"Message not delivered to topic in {TIMEOUT}s.")

        end_time = time.monotonic()

        elapsed = end_time - start_time

        assert consumed_message is not None
        assert consumed_message.payload == payload
        assert elapsed < 1.0  # Should be very fast

    async def test_delayed_message_retains_key_and_headers(self, provider_factory):
        """
        Verifies that the original key and headers are preserved on a
        delayed message.
        """
        publish, get_message_from_topic = provider_factory
        destination_topic = f"tck-delayed-test-{uuid.uuid4()}"
        key = f"key-{uuid.uuid4()}"
        headers = {"x-trace-id": str(uuid.uuid4())}
        delay_seconds = 2.0

        await publish(
            topic=destination_topic,
            payload=b"delayed with context",
            key=key,
            headers=headers,
            delay_seconds=delay_seconds,
        )

        TIMEOUT = 3.0
        try:
            consumed_message = await asyncio.wait_for(
                get_message_from_topic(destination_topic), timeout=TIMEOUT
            )
        except TimeoutError:
            pytest.fail(f"Message not delivered to topic in {TIMEOUT}s.")

        assert consumed_message is not None
        assert consumed_message.key == key

        # Check for header preservation
        for h_key, h_value in headers.items():
            assert h_key in consumed_message.headers
            header_value = consumed_message.headers[h_key]
            if isinstance(header_value, bytes):
                header_value = header_value.decode("utf-8")
            assert header_value == h_value
