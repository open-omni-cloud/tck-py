# tests/reference/messaging/test_in_memory_delayed_messaging.py
import asyncio
import contextlib
import time
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any, NamedTuple

import pytest

# TCK Contract Imports
from tck_py.messaging.delayed_messaging import BaseTestDelayedMessagingContract
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
            return await asyncio.wait_for(self._topics[topic].get(), timeout=5.0)
        except TimeoutError:
            return None


# =============================================================================
# 2. DELAYED MESSAGING PROVIDER IMPLEMENTATION
# =============================================================================


class DelayedMessage(NamedTuple):
    """Internal representation of a message waiting for its delay."""

    delivery_time: float
    destination_topic: str
    message: ConsumedMessage


class InMemoryDelayedPublisher:
    """
    Implements the republisher pattern in memory.
    """

    def __init__(self, broker: InMemoryBroker):
        self._broker = broker
        self._waiting_room: list[DelayedMessage] = []
        self._active = True
        self._republisher_task = asyncio.create_task(self._republisher_loop())

    async def publish(
        self,
        topic: str,
        payload: bytes,
        key: str | None,
        headers: dict | None,
        delay_seconds: float | None,
    ):
        message = ConsumedMessage(payload=payload, key=key, headers=headers or {})

        if not delay_seconds or delay_seconds <= 0:
            await self._broker.publish(topic, message)
            return

        delivery_time = time.monotonic() + delay_seconds
        delayed_message = DelayedMessage(
            delivery_time=delivery_time, destination_topic=topic, message=message
        )
        self._waiting_room.append(delayed_message)

    async def _republisher_loop(self):
        while self._active:
            now = time.monotonic()
            ready_to_publish = []

            # Find messages whose time has come
            for msg in self._waiting_room:
                if now >= msg.delivery_time:
                    ready_to_publish.append(msg)

            # Publish them and remove from waiting room
            if ready_to_publish:
                for msg in ready_to_publish:
                    await self._broker.publish(msg.destination_topic, msg.message)
                    self._waiting_room.remove(msg)

            await asyncio.sleep(0.1)

    async def stop(self):
        """Gracefully stops the background republisher task."""
        self._active = False
        self._republisher_task.cancel()

        try:
            await self._republisher_task
        except asyncio.CancelledError:
            # Re-raise explicit to satisfy SonarQube rule
            raise
        except Exception:
            pass

        await asyncio.sleep(0.01)


# =============================================================================
# 3. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryDelayedMessagingCompliance(BaseTestDelayedMessagingContract):
    """
    Runs the full Delayed Messaging TCK compliance suite against the
    in-memory republisher implementation.
    """

    @pytest.fixture
    async def provider_factory(self) -> AsyncGenerator[Any, Any]:
        """
        Provides the TCK with a fully operational delayed messaging system.
        """
        broker = InMemoryBroker()
        publisher = InMemoryDelayedPublisher(broker)

        async def publish_func(
            topic, payload, key=None, headers=None, delay_seconds=None
        ):
            await publisher.publish(topic, payload, key, headers, delay_seconds)

        async def get_message_from_topic(topic: str):
            # The abstract test handles the asyncio.wait_for context manager
            return await broker._topics[topic].get()

        yield publish_func, get_message_from_topic

        # Teardown: absorb the CancelledError here at fixture boundary
        with contextlib.suppress(asyncio.CancelledError):
            await publisher.stop()

    async def test_message_is_delivered_after_delay(self, provider_factory):
        await super().test_message_is_delivered_after_delay(provider_factory)

    async def test_message_without_delay_is_delivered_immediately(
        self, provider_factory
    ):
        await super().test_message_without_delay_is_delivered_immediately(
            provider_factory
        )

    async def test_delayed_message_retains_key_and_headers(self, provider_factory):
        await super().test_delayed_message_retains_key_and_headers(provider_factory)
