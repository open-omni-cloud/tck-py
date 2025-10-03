# src/tck_py/messaging/consumer.py
import asyncio
import uuid
from collections.abc import Awaitable, Callable
from enum import Enum, auto
from typing import Any

import pytest


class ProcessingOutcome(Enum):
    """
    Standardized outcomes that a message handler can return
    to the consumer wrapper.
    """

    SUCCESS = auto()
    RETRY = auto()
    FAIL = auto()


@pytest.mark.asyncio
class BaseTestConsumerContract:
    """
    TCK Contract: Defines the compliance test suite for any provider
    implementing a message consumer, including resilience behaviors.
    """

    @pytest.fixture
    def provider_factory(
        self,
    ) -> Callable[..., Awaitable[tuple[Any, Callable, Callable]]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function. This factory accepts:
        1. `handler (Callable)`: The async function to be called
           with the consumed message.
        2. `topic (str)`: The topic to subscribe to.
        3. `consumer_config (dict)`: A dict for provider-specific settings,
           like `max_attempts` for retry/dlq tests.
        When awaited, the factory must return a tuple of three items:

        1. A running `consumer` instance/task.
        2. An async `publish_func(payload, key, headers)` to send messages.
        3. An async `get_message_from_dlq(timeout)` to verify DLQ functionality.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Basic Consumption Tests ---

    async def test_consumes_simple_message(self, provider_factory):
        """
        Verifies that a consumer receives a simple message and the handler
        is called with the correct payload.
        """
        topic = f"tck-consumer-test-{uuid.uuid4()}"
        payload = b"test-payload"
        results_queue = asyncio.Queue()

        async def handler(message: Any):
            await results_queue.put(message.payload)
            return ProcessingOutcome.SUCCESS

        consumer_task, publish, _ = await provider_factory(handler, topic, {})

        try:
            await publish(payload=payload, key=None, headers=None)
            # Timeout enforced here by asyncio.wait_for
            consumed_payload = await asyncio.wait_for(results_queue.get(), timeout=2.0)
            assert consumed_payload == payload
        finally:
            consumer_task.cancel()
            await asyncio.sleep(0.01)

    async def test_consumes_message_with_key_and_headers(self, provider_factory):
        """
        Verifies that the key and headers of a message are correctly
        delivered to the handler.
        """
        topic = f"tck-consumer-test-{uuid.uuid4()}"
        key = f"message-key-{uuid.uuid4()}"
        headers = {"x-trace-id": str(uuid.uuid4())}
        results_queue = asyncio.Queue()

        async def handler(message: Any):
            await results_queue.put((message.key, message.headers))
            return ProcessingOutcome.SUCCESS

        consumer_task, publish, _ = await provider_factory(handler, topic, {})

        try:
            await publish(payload=b"data", key=key, headers=headers)
            # Timeout enforced here by asyncio.wait_for
            consumed_key, consumed_headers = await asyncio.wait_for(
                results_queue.get(), timeout=2.0
            )

            assert consumed_key == key
            for h_key, h_value in headers.items():
                assert h_key in consumed_headers
                header_value = consumed_headers[h_key]
                if isinstance(header_value, bytes):
                    header_value = header_value.decode("utf-8")
                assert header_value == h_value
        finally:
            consumer_task.cancel()
            await asyncio.sleep(0.01)

    # --- Resilience Tests ---

    async def test_retry_outcome_redelivers_message(self, provider_factory):
        """
        Verifies that when a handler returns RETRY, the same message is
        delivered again to the handler.
        """
        topic = f"tck-consumer-retry-{uuid.uuid4()}"
        payload = b"plz-retry-me"
        results_queue = asyncio.Queue()
        call_count = 0

        async def handler(message: Any):
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                return ProcessingOutcome.RETRY

            # On the second attempt, succeed and put to queue
            await results_queue.put(message.payload)
            return ProcessingOutcome.SUCCESS

        consumer_task, publish, _ = await provider_factory(
            handler, topic, {"max_attempts": 2}
        )

        try:
            await publish(payload=payload)

            # The test will only pass if the message is redelivered and the
            # handler succeeds on the second try.
            # Enforce the timeout using asyncio.wait_for.
            consumed_payload = await asyncio.wait_for(results_queue.get(), timeout=2.5)

            assert call_count == 2
            assert consumed_payload == payload
        finally:
            consumer_task.cancel()
            await asyncio.sleep(0.01)

    async def test_fail_outcome_moves_message_to_dlq(self, provider_factory):
        """
        Verifies that after exhausting retries, a message is sent to the DLQ.
        """
        topic = f"tck-consumer-dlq-{uuid.uuid4()}"
        payload = b"i-will-fail"
        key = f"dlq-key-{uuid.uuid4()}"

        # This handler always fails, forcing the message through the retry
        # process and eventually into the DLQ.
        async def handler(message: Any):
            await asyncio.sleep(0)  # Simulate processing time
            return ProcessingOutcome.FAIL

        consumer_task, publish, get_message_from_dlq = await provider_factory(
            handler,
            topic,
            {"max_attempts": 1},  # Only 1 attempt before DLQ
        )

        try:
            await publish(payload=payload, key=key)

            # Wait for the message to be processed and sent to DLQ
            # Enforce the timeout here.
            dlq_message = await asyncio.wait_for(
                get_message_from_dlq(timeout=2.5), timeout=2.5
            )

            assert dlq_message is not None
            assert dlq_message.payload == payload
            assert dlq_message.key == key
        finally:
            consumer_task.cancel()
            await asyncio.sleep(0.01)
