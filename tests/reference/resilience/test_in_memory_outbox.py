# tests/reference/resilience/test_in_memory_outbox.py
import asyncio
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.resilience.transactional_outbox import BaseTestOutboxStorageContract
from tck_py.shared.models import OutboxEvent

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemoryOutboxRepository:
    """
    In-memory implementation of the OutboxStorageProtocol.
    Simulates an outbox table and a sequence generator to ensure FIFO
    ordering for events within the same aggregate.
    """

    def __init__(self):
        # { event_id: full_event_dict_object }
        self._events: dict[str, dict] = {}
        # { aggregate_key: last_sequence_id }
        self._sequences: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    def _dict_to_model(self, event_dict: dict) -> OutboxEvent:
        """Helper to convert the internal dictionary
        representation back to the canonical OutboxEvent model."""
        return OutboxEvent(
            destination_topic=event_dict["destination_topic"],
            payload=event_dict["payload"],
            message_key=event_dict.get("message_key"),
            aggregate_key=event_dict.get("aggregate_key"),
        )

    def _dict_to_outbox_model(self, event_dict: dict) -> dict:
        """Helper to return the dictionary, but ensure it
        contains all required TCK fields for assertion."""
        # The TCK tests check attributes like sequence_id and status
        # directly on the dictionary when returned by the provider,
        # but the *data* inside the dict should match the model fields.
        # This function ensures we return the necessary
        # fields for TCK assertions.
        return {
            "event_id": event_dict["event_id"],
            "aggregate_key": event_dict.get("aggregate_key"),
            "destination_topic": event_dict["destination_topic"],
            "payload": event_dict["payload"],
            "message_key": event_dict.get("message_key"),
            "status": event_dict["status"],
            "sequence_id": event_dict.get("sequence_id"),
        }

    async def save_event(self, event: OutboxEvent):
        async with self._lock:
            event_id = str(uuid.uuid4())
            sequence_id = None

            if event.aggregate_key:
                self._sequences[event.aggregate_key] += 1
                sequence_id = self._sequences[event.aggregate_key]

            self._events[event_id] = {
                "event_id": event_id,
                "aggregate_key": event.aggregate_key,
                "destination_topic": event.destination_topic,
                "payload": event.payload,
                "message_key": event.message_key,
                "status": "PENDING",
                "sequence_id": sequence_id,
            }

    async def get_pending_unordered_events(self, limit: int) -> list[dict]:
        results = []
        for event in self._events.values():
            if event["status"] == "PENDING" and event["aggregate_key"] is None:
                results.append(self._dict_to_outbox_model(event))
                if len(results) == limit:
                    await asyncio.sleep(0)
                    break
        return results

    async def get_pending_aggregate_keys(self) -> list[str]:
        keys = set()
        for event in self._events.values():
            if event["status"] == "PENDING" and event["aggregate_key"] is not None:
                keys.add(event["aggregate_key"])

        await asyncio.sleep(0)

        return sorted(keys)

    async def get_pending_events_for_aggregate(self, aggregate_key: str) -> list[dict]:
        results = []
        for event in self._events.values():
            if event["status"] == "PENDING" and event["aggregate_key"] == aggregate_key:
                results.append(self._dict_to_outbox_model(event))

        await asyncio.sleep(0)

        # Sort by sequence_id to guarantee order
        return sorted(results, key=lambda e: e["sequence_id"])

    async def mark_as_processed(self, event: dict):
        event_id = event["event_id"]
        if event_id in self._events:
            self._events[event_id]["status"] = "PROCESSED"
            await asyncio.sleep(0)


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryOutboxCompliance(BaseTestOutboxStorageContract):
    """
    Runs the full Transactional Outbox TCK compliance suite against the
    in-memory repository implementation.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        Provides the TCK with instances of our InMemoryOutboxRepository.
        """

        async def _factory(**config):
            # A new instance is created for each test, ensuring a clean state.
            await asyncio.sleep(0)
            return InMemoryOutboxRepository()

        return _factory
