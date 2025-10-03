# User Guide: Implementing the Saga State Repository Contract

The Saga pattern is a mechanism for managing data consistency across multiple microservices in a distributed transaction.
Instead of using traditional (and often impractical) two-phase commits, a saga is a sequence of local transactions where each step has a corresponding compensating action for rollbacks.
This TCK contract validates the **Saga State Repository**, the persistence layer responsible for tracking the progress of every running saga instance.
A reliable repository is the backbone of any saga implementation.

## Contract Overview

**TCK Class:** ```tck_py.resilience.sagas.BaseTestSagaStateRepositoryContract```

The `BaseTestSagaStateRepositoryContract` validates the correct creation, retrieval, and updating of a saga's state.
Its most critical function is to verify the provider's implementation of **Optimistic Concurrency Control (OCC)**, which is essential for preventing race conditions and ensuring data integrity.

## Implementing the Fixture: `provider_factory`

Your fixture must provide a clean instance of your saga state repository for each test.
The repository is expected to handle the persistence of `SagaState` objects.

```info
The TCK's `SagaState` model includes a `version` field.
Your provider's `update_state` method **must** use this field to prevent stale writes, typically by including it in the `WHERE` clause of an update statement (e.g., `UPDATE ... WHERE saga_id = ? AND version = ?`).
```

### Example Fixture Implementation

Let's assume a `MongoSagaRepository` that stores saga state in a MongoDB collection.
```python
# tests/compliance/test_mongo_saga_repo_compliance.py
import pytest
from tck_py.resilience.sagas import BaseTestSagaStateRepositoryContract
from my_project.repositories.mongo_saga import MongoSagaRepository

@pytest.fixture
async def test_mongo_db():
    # Setup code to connect to a test MongoDB
    db = ...
    await db["saga_state"].delete_many({}) # Clean the collection
    yield db
    ...

class TestMongoSagaRepoCompliance(BaseTestSagaStateRepositoryContract):

    @pytest.fixture
    def provider_factory(self, test_mongo_db):
        """
        Provides the TCK with instances of our MongoSagaRepository.
        """
        async def _factory(**config):
            return MongoSagaRepository(database=test_mongo_db)

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `BaseTestSagaStateRepositoryContract` and will be run against your provider.

---

### `test_create_and_get_saga_state`

-   **Purpose**: Verifies the basic creation and retrieval of a saga's initial state.
-   **Behavior**: The test calls `await provider.create_state()` with a new `SagaState` object (with `version=0`).
It then calls `await provider.get_state()` for the same `saga_id`.
-   **Requirement**: The retrieved state must match the initial data, and its `version` must be automatically set to `1` by the `create_state` method.
---

### `test_get_non_existent_saga_returns_none`

-   **Purpose**: Ensures the repository handles lookups for non-existent sagas gracefully.
-   **Behavior**: The test calls `await provider.get_state()` with a random `saga_id`. It **must** return `None`.
---

### `test_update_saga_state_increments_version`

-   **Purpose**: Validates the successful state update path.
-   **Behavior**: The test creates a state, retrieves it (now at `version=1`), modifies it (e.g., advances the `current_step`), and calls `await provider.update_state()`.
-   **Requirement**: A final `get_state` call must show that the data was updated and the `version` has been incremented to `2`.
---

### `test_update_with_stale_version_raises_conflict_error`

-   **Purpose**: **This is the most critical test in the contract.** It validates the optimistic concurrency control mechanism, which prevents data corruption from race conditions.
-   **Behavior**: The test simulates two concurrent processes:
    1.  It loads the same saga state (`version=1`) into two variables, `process_a_state` and `process_b_state`.
    2.  It successfully updates the state using `process_a_state`. The state in the database is now at `version=2`.
    3.  It then attempts to update the state again, but this time using `process_b_state`, which is now stale (it still has `version=1`).
-   **Requirement**: This second update attempt **must** fail by raising the TCK's standardized ```tck_py.shared.exceptions.SagaStateConflictError```.
The test also verifies that the stale data from process B was not persisted.
