# User Guide: Implementing the Key-Value Store Contract

The Key-Value (KV) Store is one of the most fundamental infrastructure primitives in the Open Omni-Cloud standard. This guide details how to implement a compliant KV store provider by satisfying the `TestKVStoreContract` from the TCK.

## Contract Overview

**TCK Class:** ```tck_py.primitives.kv_store.TestKVStoreContract```

The `TestKVStoreContract` validates the essential behaviors of a key-value database, such as `set`, `get`, `delete`, and ensures that operations are idempotent where required. Any provider that passes this suite can be used as a reliable, interchangeable backend for simple key-value storage.

## Implementing the Fixture: `provider_factory`

To run the TCK compliance suite, you must implement the `provider_factory` fixture. This fixture is the bridge between the TCK and your provider implementation.

```info
The factory must return an **async function** that, when awaited, provides a clean, initialized instance of your provider for each test. This ensures test isolation.
```

### Example Fixture Implementation

Let's assume you have a `RedisKVStore` provider that connects to a Redis instance. Your compliance test file would look like this:

```python
# tests/compliance/test_redis_kv_compliance.py
import pytest
from tck_py.primitives.kv_store import TestKVStoreContract
from my_project.providers.redis_kv import RedisKVStore

# You might use a fixture to manage a test Redis instance (e.g., via Docker)
@pytest.fixture
async def test_redis_client():
    # Setup code to connect to a test Redis
    client = ...
    await client.flushdb() # Ensure DB is clean before test
    yield client
    # Teardown code
    await client.close()

class TestRedisKVStoreCompliance(TestKVStoreContract):

    @pytest.fixture
    def provider_factory(self, test_redis_client):
        """
        This factory provides the TCK with instances of our RedisKVStore.
        """
        async def _factory(**config):
            # The factory should return a fresh provider instance for each test
            return RedisKVStore(client=test_redis_client)

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `TestKVStoreContract` and will be run against your provider.

---

### `test_set_and_get_value`

-   **Purpose**: Verifies the most basic `set` and `get` functionality.
-   **Behavior**: The test will call `await provider.set(key, value)` and then `await provider.get(key)`, asserting that the retrieved value matches the original.

---

### `test_get_non_existent_key_returns_none`

-   **Purpose**: Ensures that your provider correctly handles a cache miss scenario.
-   **Behavior**: The test calls `await provider.get()` on a key that has not been set. It **must** return `None` and must **not** raise an exception.

---

### `test_set_overwrites_existing_value`

-   **Purpose**: Validates that the `set` operation is an upsert (update or insert).
-   **Behavior**: The test will set an initial value for a key, then call `set` again on the same key with a new value. A final `get` must return the new value.

---

### `test_delete_removes_key`

-   **Purpose**: Verifies the `delete` operation.
-   **Behavior**: The test will `set` a key, `delete` it, and then `get` it again, asserting that the result is now `None`.

---

### `test_delete_is_idempotent`

-   **Purpose**: This is a critical idempotency test. It ensures that your provider can be used safely in automated scripts where a delete operation might be called multiple times.
-   **Behavior**: The test calls `await provider.delete()` on a key that does not exist. The operation **must** complete successfully without raising any exceptions.

---

### `test_set_is_idempotent`

-   **Purpose**: Another critical idempotency test for write operations.
-   **Behavior**: The test calls `await provider.set(key, value)` multiple times with the exact same arguments. A final `get` must return the correct value, and the state of the system should be as if `set` was only called once.
