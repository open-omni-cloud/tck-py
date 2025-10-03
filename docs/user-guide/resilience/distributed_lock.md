# User Guide: Implementing the Distributed Lock Contract

A distributed lock is a fundamental resilience primitive used to ensure that only one process can access a critical resource at a time in a distributed environment.
This is essential for preventing race conditions and ensuring data consistency during critical operations.
This guide details how to implement a compliant distributed lock provider by satisfying the `BaseTestDistributedLockContract`.

## Contract Overview

**TCK Class:** ```tck_py.resilience.distributed_lock.BaseTestDistributedLockContract```

The `BaseTestDistributedLockContract` validates the core behaviors of a distributed lock:
1.  **Mutual Exclusion**: Only one client can hold the lock at a time.
2.  **TTL Expiration**: Locks are automatically released after a timeout to prevent deadlocks.
3.  **Pythonic Usage**: The lock can be used as an async context manager (`async with`).

## Implementing the Fixture: `lock_manager_factory`

Your fixture must provide a "lock manager" object.
This manager is responsible for creating individual lock instances for specific resource names.
```info
The factory must return an **async function** that, when awaited, provides a lock manager.
This manager must have a method like `get_lock(lock_name: str, ttl: int)` which returns a lock object.
The lock object itself must implement `acquire()` and `release()` methods, and also support the `async with` statement.
```

### Example Fixture Implementation

Let's assume a `RedisLockManager` that uses Redis to implement distributed locking.
```python
# tests/compliance/test_redis_lock_compliance.py
import pytest
from tck_py.resilience.distributed_lock import BaseTestDistributedLockContract
from my_project.resilience.redis_lock import RedisLockManager

@pytest.fixture
async def test_redis_client():
    # Setup code to connect to a test Redis
    client = ...
    await client.flushdb()
    yield client
    await client.close()

class TestRedisLockCompliance(BaseTestDistributedLockContract):

    @pytest.fixture
    def lock_manager_factory(self, test_redis_client):
        """
        Provides the TCK with instances of our RedisLockManager.
        """
        async def _factory(**config):
            # The factory returns the manager, which can then create locks
            return RedisLockManager(client=test_redis_client)

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `BaseTestDistributedLockContract` and will be run against your provider.

---

### `test_acquire_and_release_lock`

-   **Purpose**: Verifies the basic lock lifecycle.
-   **Behavior**: The test acquires a new lock, asserts that the acquisition was successful (`acquire()` returns `True`), releases it, and then acquires it again successfully to ensure the release worked.
---

### `test_mutual_exclusion`

-   **Purpose**: **This is the core test of the contract.** It validates that the lock correctly enforces exclusive access.
-   **Behavior**: The test simulates two clients. Client 1 acquires the lock.
Then, Client 2 attempts to acquire the **same lock** and must fail (`acquire()` must return `False`).
After Client 1 releases the lock, Client 2 must then be able to acquire it successfully.
---

### `test_lock_expires_after_ttl`

-   **Purpose**: A critical safety test to ensure your lock implementation prevents deadlocks.
-   **Behavior**: The test simulates a client that acquires a lock with a short TTL (e.g., 1 second) and then "crashes" (i.e., it never calls `release()`).
The test then waits for the TTL to pass and asserts that a second client can now successfully acquire the lock.
-   **Requirement**: Your provider **must** enforce the TTL, automatically releasing the lock after the specified time.
---

### `test_lock_as_async_context_manager`

-   **Purpose**: Ensures the lock provides a clean, Pythonic interface that guarantees the lock is released.
-   **Behavior**: The test uses the lock in an `async with` block.
Inside the block, it verifies the lock is held. After the block exits (either normally or via an exception), the test verifies that the lock has been automatically released and can be acquired again.
---

### `test_release_is_idempotent`

-   **Purpose**: Verifies that releasing an already-released lock is a safe, idempotent operation.
-   **Behavior**: The test acquires and releases a lock, then attempts to release it a second time.
-   **Requirement**: The second release attempt **must** not raise an exception.
