# User Guide: Implementing the Cache Contract

The Cache contract defines the standard interface for providers of fast, in-memory or near-memory data storage with automatic expiration. Caching is a critical component for improving application performance by reducing latency to slower backend systems.

This guide details how to implement a compliant cache provider by satisfying the `TestCacheContract`.

## Contract Overview

**TCK Class:** ```tck_py.primitives.cache.TestCacheContract```

The `TestCacheContract` validates the core behavior of a cache. While it includes basic `set` and `get` tests, its most critical role is to verify the **Time To Live (TTL)** functionality, ensuring that cached items expire correctly after their designated lifetime.

## Implementing the Fixture: `provider_factory`

You must implement the `provider_factory` fixture to run the compliance suite. It should provide a clean cache instance for every test.

```info
For providers like Redis or Memcached, it's essential that your fixture provides a connection to a clean database or namespace for each test run to prevent test contamination. A `flushdb` or similar command is highly recommended.
```

### Example Fixture Implementation

Here is an example for a `RedisCacheProvider`, which would be very similar to a `RedisKVStore` provider.

```python
# tests/compliance/test_redis_cache_compliance.py
import pytest
from tck_py.primitives.cache import TestCacheContract
from my_project.providers.redis_cache import RedisCacheProvider

@pytest.fixture
async def test_redis_client():
    # Setup code to connect to a test Redis
    client = ...
    await client.flushdb() # CRITICAL: Ensure cache is clean
    yield client
    await client.close()

class TestRedisCacheCompliance(TestCacheContract):

    @pytest.fixture
    def provider_factory(self, test_redis_client):
        """
        This factory provides the TCK with instances of our RedisCacheProvider.
        """
        async def _factory(**config):
            return RedisCacheProvider(client=test_redis_client)

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `TestCacheContract` and will be run against your provider.

---

### `test_set_and_get_value_without_ttl`

-   **Purpose**: Verifies that your provider can function as a simple persistent store if no TTL is provided.
-   **Behavior**: The test calls `await provider.set(key, value, ttl=None)`. A subsequent `get` for that key must return the correct value.

---

### `test_get_non_existent_key_is_a_cache_miss`

-   **Purpose**: Ensures the provider correctly handles a cache miss.
-   **Behavior**: The test calls `await provider.get()` on a key that does not exist. It **must** return `None`.

---

### `test_key_expires_after_ttl`

-   **Purpose**: **This is the most important test in the contract.** It validates the core purpose of a cache.
-   **Behavior**: The test calls `await provider.set(key, value, ttl=1)`. It then pauses execution for slightly more than 1 second (`asyncio.sleep(1.1)`). Finally, it calls `await provider.get(key)` and asserts that the result is `None`, because the item should have expired.

---

### `test_delete_removes_key_before_expiry`

-   **Purpose**: Verifies that an item can be explicitly invalidated before its TTL is up.
-   **Behavior**: The test sets a key with a long TTL (e.g., 10 seconds), then immediately calls `await provider.delete(key)`. A subsequent `get` must return `None`.

---

### `test_set_overwrites_existing_value_and_ttl`

-   **Purpose**: Ensures that re-setting a key can also update its expiration policy.
-   **Behavior**: The test sets a key with a long TTL (e.g., 60 seconds). It then immediately calls `set` again on the same key with a new value and a very short TTL (1 second). After waiting for the short TTL to expire, a `get` call must return `None`, proving that the TTL was successfully updated.
