# User Guide: Implementing the Transactional Outbox Contract

The Transactional Outbox is one of the most critical resilience patterns for building reliable microservices.
It solves the dual-write problem by guaranteeing that an event will be published *if and only if* the corresponding business transaction is successfully committed.
This TCK contract does not test the entire pattern, but its foundational layer: the **Outbox Storage Repository**.
It ensures that any database backend used for the outbox table/collection behaves predictably and provides the strict ordering guarantees the pattern relies on.

## Contract Overview

**TCK Class:** ```tck_py.resilience.transactional_outbox.BaseTestOutboxStorageContract```

The `BaseTestOutboxStorageContract` validates the correct persistence of outbox events, the state transition from "pending" to "processed," and, most importantly, the **atomic, sequential ID generation for ordered events** belonging to the same aggregate.

## Implementing the Fixture: `provider_factory`

Your fixture must provide a clean instance of your outbox storage repository for each test.
```info
Similar to other persistence contracts, your fixture should ensure the underlying database table or collection is clean before each test run to guarantee test isolation.
```

### Example Fixture Implementation

Let's assume you are building an `MongoOutboxRepository` on top of a generic MongoDB client.
```python
# tests/compliance/test_mongo_outbox_compliance.py
import pytest
from tck_py.resilience.transactional_outbox import BaseTestOutboxStorageContract
from my_project.repositories.mongo_outbox import MongoOutboxRepository

@pytest.fixture
async def test_mongo_db():
    # Setup code to connect to a test MongoDB and get a database object
    db = ...
    # Clean up all relevant collections before the test
    await db["outbox_events"].delete_many({})
    await db["outbox_sequences"].delete_many({})
    yield db
    # Teardown logic
    ...

class TestMongoOutboxCompliance(BaseTestOutboxStorageContract):

    @pytest.fixture
    def provider_factory(self, test_mongo_db):
        """
        This factory provides the TCK with instances of our MongoOutboxRepository.
        """
        async def _factory(**config):
            return MongoOutboxRepository(database=test_mongo_db)

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `BaseTestOutboxStorageContract` and will be run against your provider.

---

### `test_save_and_retrieve_unordered_event`

-   **Purpose**: Verifies that a standard, unordered event is correctly saved and can be retrieved for processing.
-   **Behavior**: The test calls `await provider.save_event()` with a simple event.
It then calls `await provider.get_pending_unordered_events()` and asserts that the saved event is present in the results.
---

### `test_mark_as_processed_removes_from_pending`

-   **Purpose**: Validates the state transition of an event from pending to processed.
-   **Behavior**: The test saves an event, retrieves it, and then calls `await provider.mark_as_processed()` on the event object.
A subsequent call to `get_pending_unordered_events()` must return an empty list.
---

### `test_sequential_id_generation_for_ordered_events`

-   **Purpose**: **This is the most critical test in the contract.** It verifies the guarantee of First-In, First-Out (FIFO) processing for events related to the same business entity (aggregate).
-   **Behavior**: The test saves multiple events in quick succession, all with the same `aggregate_key`.
It then retrieves all pending events for that aggregate.
-   **Requirement**: Your provider **must** atomically assign a `sequence_id` to each event within the scope of its `aggregate_key`, starting from 1. The test asserts that the retrieved events have `sequence_id` values of `[1, 2, 3, ...]`.
---

### `test_sequence_ids_are_independent_per_aggregate`

-   **Purpose**: Ensures that the sequencing for one aggregate does not interfere with another.
-   **Behavior**: The test interleaves saving events for two different `aggregate_key` values.
It then verifies that the `sequence_id` for each aggregate is independent and correctly starts from 1 for both.
---

### `test_get_pending_aggregate_keys`

-   **Purpose**: Validates the discovery mechanism that the outbox publisher service uses to find which aggregates have ordered events waiting to be processed.
-   **Behavior**: The test saves events for multiple different aggregates.
It then calls `await provider.get_pending_aggregate_keys()` and asserts that the returned list contains all the unique aggregate keys that have pending events.
---

### `test_mark_as_processed_is_idempotent`

-   **Purpose**: Ensures that re-marking an already-processed event is a safe, non-destructive operation.
-   **Behavior**: The test calls `await provider.mark_as_processed()` on the same event object multiple times.
-   **Requirement**: The operation **must** complete successfully without raising any exceptions.
