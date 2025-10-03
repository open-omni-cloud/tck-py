# src/tck_py/resilience/distributed_lock.py
import asyncio  # New Import for explicit sleep
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest


@pytest.mark.asyncio
class BaseTestDistributedLockContract:
    """
    TCK Contract: Defines the compliance test suite for
    any provider
    implementing the DistributedLockProtocol.

    This contract verifies mutual exclusion, release, and TTL-based expiration.
    A lock provider is expected to return a lock object that can be used
    as an async context manager.
    """

    @pytest.fixture
    def lock_manager_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function that, when awaited,
        returns a lock manager instance. This manager must have a method like
        `get_lock(lock_name: str, ttl: int)` which returns a lock object.
        The lock object must have `acquire()` and `release()` async methods.
        `acquire()` should return True if the lock is acquired, False otherwise.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'lock_manager_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_acquire_and_release_lock(self, lock_manager_factory):
        """
        Verifies the basic workflow of acquiring and releasing a lock.
        """
        lock_manager = await lock_manager_factory()
        lock_name = f"tck-lock-{uuid.uuid4()}"

        lock = lock_manager.get_lock(lock_name, ttl=10)

        # Acquire the lock
        acquired = await lock.acquire()
        assert acquired is True, "Should be able to acquire a new lock."

        # Release the lock
        await lock.release()

        # Should be able to acquire it again after release
        re_acquired = await lock.acquire()
        assert (
            re_acquired is True
        ), "Should be able to re-acquire the lock after releasing it."
        await lock.release()

    async def test_mutual_exclusion(self, lock_manager_factory):
        """
        Verifies that once a lock is acquired, a second attempt to acquire
        the same lock fails (returns False).
        """
        lock_manager = await lock_manager_factory()
        lock_name = f"tck-lock-{uuid.uuid4()}"

        lock1 = lock_manager.get_lock(lock_name, ttl=10)
        lock2 = lock_manager.get_lock(lock_name, ttl=10)

        # First client acquires the lock
        acquired1 = await lock1.acquire()
        assert acquired1 is True

        # Second client attempts to acquire the same lock and should fail
        acquired2 = await lock2.acquire()
        assert (
            acquired2 is False
        ), "A second client should not be able to acquire a held lock."

        # First client releases the lock
        await lock1.release()

        # Now the second client should be able to acquire it
        acquired2_after_release = await lock2.acquire()
        assert (
            acquired2_after_release is True
        ), "Should be able to acquire the lock after it was released."
        await lock2.release()

    async def test_lock_expires_after_ttl(self, lock_manager_factory):
        """
        Verifies that a lock is automatically released after its TTL expires,
        preventing deadlocks.
        """
        lock_manager = await lock_manager_factory()
        lock_name = f"tck-lock-{uuid.uuid4()}"
        ttl_seconds = 1

        lock1 = lock_manager.get_lock(lock_name, ttl=ttl_seconds)
        lock2 = lock_manager.get_lock(lock_name, ttl=ttl_seconds)

        # Acquire the lock but do not release it
        assert await lock1.acquire() is True

        # Wait for the TTL to expire
        await asyncio.sleep(ttl_seconds + 0.2)

        # lock1 should have expired, so lock2 should now be able to acquire it
        acquired2 = await lock2.acquire()
        assert (
            acquired2 is True
        ), "Should be able to acquire the lock after the first one's TTL expired."
        await lock2.release()

    async def test_lock_as_async_context_manager(self, lock_manager_factory):
        """
        Verifies that the lock object can be used as an async context manager,
        automating the release.
        """
        lock_manager = await lock_manager_factory()
        lock_name = f"tck-lock-{uuid.uuid4()}"

        lock = lock_manager.get_lock(lock_name, ttl=10)

        async with lock as acquired:
            assert (
                acquired is True
            ), "Lock should be acquired within the context manager."

            # Verify it's actually locked inside the context
            same_lock_again = lock_manager.get_lock(lock_name, ttl=10)
            assert await same_lock_again.acquire() is False

        # After the context exits, the lock should be released and available again
        assert (
            await same_lock_again.acquire() is True
        ), "Lock should be released after exiting the context."
        await same_lock_again.release()

    async def test_release_is_idempotent(self, lock_manager_factory):
        """
        Verifies that releasing an already-released lock does not raise an error.
        """
        lock_manager = await lock_manager_factory()
        lock_name = f"tck-lock-{uuid.uuid4()}"

        lock = lock_manager.get_lock(lock_name, ttl=10)

        assert await lock.acquire() is True

        # Release multiple times
        await lock.release()
        try:
            await lock.release()
        except Exception as e:
            pytest.fail(
                "Releasing an already-released lock raised "
                f"an unexpected exception: {e}"
            )

        # To confirm the state is correct, we should still be able to acquire the lock
        assert await lock.acquire() is True
        await lock.release()
