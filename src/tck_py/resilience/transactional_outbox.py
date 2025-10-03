# src/tck_py/resilience/transactional_outbox.py
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from tck_py.shared.models import OutboxEvent


@pytest.mark.asyncio
class BaseTestOutboxStorageContract:
    """
    TCK Contract: Defines the compliance test suite for any storage provider
    implementing the OutboxStorageProtocol.

    This contract verifies the atomicity and ordering guarantees required
    by the Transactional Outbox pattern.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function that, when awaited,
        returns a new, clean instance of the outbox storage provider to be tested.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_save_and_retrieve_unordered_event(self, provider_factory):
        """
        Verifies that a simple event without an aggregate_key can be saved
        and retrieved for unordered processing.
        """
        provider = await provider_factory()
        event = OutboxEvent(destination_topic="topic-a", payload=b"data")

        await provider.save_event(event)

        pending_events = await provider.get_pending_unordered_events(limit=10)

        assert len(pending_events) == 1
        assert pending_events[0]["payload"] == event.payload
        assert pending_events[0]["destination_topic"] == event.destination_topic

    async def test_mark_as_processed_removes_from_pending(self, provider_factory):
        """
        Verifies that after an event is marked as processed, it is no longer
        retrieved as a pending event.
        """
        provider = await provider_factory()
        event = OutboxEvent(destination_topic="topic-b", payload=b"data")
        await provider.save_event(event)

        pending_events = await provider.get_pending_unordered_events(limit=10)
        assert len(pending_events) == 1

        event_to_mark = pending_events[0]
        await provider.mark_as_processed(event_to_mark)

        final_pending_events = await provider.get_pending_unordered_events(limit=10)
        assert len(final_pending_events) == 0

    async def test_sequential_id_generation_for_ordered_events(self, provider_factory):
        """
        This is a critical test.
        It verifies that for a single aggregate_key,
        saved events are assigned sequential, ordered sequence_ids starting from 1.
        """
        provider = await provider_factory()
        agg_key = f"order-{uuid.uuid4()}"

        # Save multiple events for the same aggregate
        await provider.save_event(
            OutboxEvent(aggregate_key=agg_key, destination_topic="t", payload=b"c")
        )
        await provider.save_event(
            OutboxEvent(aggregate_key=agg_key, destination_topic="t", payload=b"d")
        )
        await provider.save_event(
            OutboxEvent(aggregate_key=agg_key, destination_topic="t", payload=b"e")
        )

        ordered_events = await provider.get_pending_events_for_aggregate(agg_key)

        assert len(ordered_events) == 3
        # Verify that sequence_id is sequential and ordered
        assert [e["sequence_id"] for e in ordered_events] == [1, 2, 3]

    async def test_sequence_ids_are_independent_per_aggregate(self, provider_factory):
        """
        Verifies that sequence_id generation for one aggregate does not
        interfere with another.
        """
        provider = await provider_factory()
        agg_key_a = f"customer-{uuid.uuid4()}"
        agg_key_b = f"product-{uuid.uuid4()}"

        # Interleave saving events for different aggregates
        await provider.save_event(
            OutboxEvent(aggregate_key=agg_key_a, destination_topic="t", payload=b"a1")
        )
        await provider.save_event(
            OutboxEvent(aggregate_key=agg_key_b, destination_topic="t", payload=b"b1")
        )
        await provider.save_event(
            OutboxEvent(aggregate_key=agg_key_a, destination_topic="t", payload=b"a2")
        )

        # Verify sequences for aggregate A
        events_a = await provider.get_pending_events_for_aggregate(agg_key_a)
        assert len(events_a) == 2
        assert [e["sequence_id"] for e in events_a] == [1, 2]

        # Verify sequence for aggregate B
        events_b = await provider.get_pending_events_for_aggregate(agg_key_b)
        assert len(events_b) == 1
        assert events_b[0]["sequence_id"] == 1

    async def test_get_pending_aggregate_keys(self, provider_factory):
        """
        Verifies the discovery mechanism for aggregates that have pending events.
        """
        provider = await provider_factory()
        agg_key_a = f"agg-{uuid.uuid4()}"
        agg_key_b = f"agg-{uuid.uuid4()}"

        await provider.save_event(
            OutboxEvent(aggregate_key=agg_key_a, destination_topic="t", payload=b"a1")
        )
        await provider.save_event(
            OutboxEvent(aggregate_key=agg_key_b, destination_topic="t", payload=b"b1")
        )
        await provider.save_event(
            OutboxEvent(destination_topic="unordered", payload=b"u1")
        )

        pending_keys = await provider.get_pending_aggregate_keys()
        assert len(pending_keys) == 2
        assert set(pending_keys) == {agg_key_a, agg_key_b}

    async def test_mark_as_processed_is_idempotent(self, provider_factory):
        """
        Verifies that marking an event as processed multiple times does not
        raise an error and the event remains processed.
        """
        provider = await provider_factory()
        event = OutboxEvent(destination_topic="topic-c", payload=b"data")
        await provider.save_event(event)

        pending_events = await provider.get_pending_unordered_events(limit=1)
        assert len(pending_events) == 1
        event_to_mark = pending_events[0]

        # Mark as processed multiple times
        await provider.mark_as_processed(event_to_mark)
        try:
            await provider.mark_as_processed(event_to_mark)
        except Exception as e:
            pytest.fail(
                f"Marking a processed event again raised an unexpected exception: {e}"
            )

        # Verify the final state is correct (the event is gone from pending)
        final_pending_events = await provider.get_pending_unordered_events(limit=10)
        assert len(final_pending_events) == 0
