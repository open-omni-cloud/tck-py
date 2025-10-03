# tests/reference/resilience/distributed_lock.py
import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.resilience.distributed_lock import (
    BaseTestDistributedLockContract,
)

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemoryLock:
    """Represents a single lock instance, controlled by a central manager."""

    def __init__(self, name: str, ttl: int, manager: "InMemoryLockManager"):
        self._name = name
        self._ttl = ttl
        self._manager = manager
        self._owner_id = str(uuid.uuid4())  # Unique ID for this attempt to acquire

    async def acquire(self) -> bool:
        return await self._manager.acquire(self._name, self._owner_id, self._ttl)

    async def release(self):
        await self._manager.release(self._name, self._owner_id)

    async def __aenter__(self):
        if not await self.acquire():
            # In a real implementation, you might wait or raise an error
            # For the TCK, we just need to reflect the acquisition status
            return False
        return True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()


class InMemoryLockManager:
    """
    Simulates a central distributed lock server.
    It holds the state of all locks (who owns them and when they expire).
    """

    def __init__(self):
        # { lock_name: (owner_id, expiration_timestamp) }
        self._locks: dict[str, tuple[str, float]] = {}
        self._global_lock = (
            asyncio.Lock()
        )  # To prevent race conditions in the manager itself

    def get_lock(self, lock_name: str, ttl: int) -> InMemoryLock:
        return InMemoryLock(lock_name, ttl, self)

    async def acquire(self, name: str, owner_id: str, ttl: int) -> bool:
        async with self._global_lock:
            current_lock = self._locks.get(name)
            now = time.monotonic()

            if current_lock is None:
                # Lock is free, acquire it
                self._locks[name] = (owner_id, now + ttl)
                return True

            _current_owner, expiration = current_lock
            if now > expiration:
                # Lock has expired, acquire it
                self._locks[name] = (owner_id, now + ttl)
                return True

            await asyncio.sleep(0)  # Simulate async operation

            # Lock is held by someone else
            return False

    async def release(self, name: str, owner_id: str):
        async with self._global_lock:
            current_lock = self._locks.get(name)
            if current_lock:
                current_owner, _ = current_lock
                # Only the owner can release the lock
                if current_owner == owner_id:
                    del self._locks[name]


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryLockCompliance(BaseTestDistributedLockContract):
    """
    Runs the full Distributed Lock TCK compliance suite against the
    in-memory implementation.
    """

    @pytest.fixture
    def lock_manager_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        Provides the TCK with instances of our InMemoryLockManager.
        """

        async def _factory(**config):
            # A new manager is created for each test to ensure isolation.
            await asyncio.sleep(0)  # Simulate async operation
            return InMemoryLockManager()

        return _factory
