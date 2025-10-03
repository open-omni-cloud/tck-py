# tests/reference/primitives/test_in_memory_cache.py
import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.primitives.cache import BaseTestCacheContract

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemoryCache:
    """
    In-memory implementation of the CacheProtocol.
    It simulates TTL by storing a tuple of (value, expiration_timestamp).
    Expired items are cleaned up lazily upon access.
    """

    def __init__(self):
        # The dictionary will store: { key: (value, expiration_timestamp) }
        # expiration_timestamp is None for items that don't expire.
        self._data: dict[str, tuple[Any, float | None]] = {}

    async def get(self, key: str) -> str | None:
        await asyncio.sleep(0)  # Simulate async operation
        item = self._data.get(key)
        if item is None:
            return None  # Cache miss

        value, expiration = item

        # Check for expiration
        if expiration is not None and time.monotonic() > expiration:
            # Item has expired, delete it and return miss
            del self._data[key]
            return None

        return value  # Cache hit

    async def set(self, key: str, value: str, ttl: int | None = None):
        expiration = None
        if ttl is not None:
            await asyncio.sleep(0)
            expiration = time.monotonic() + ttl

        self._data[key] = (value, expiration)

    async def delete(self, key: str):
        await asyncio.sleep(0)
        self._data.pop(key, None)


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryCacheCompliance(BaseTestCacheContract):
    """
    Runs the full Cache TCK compliance suite against the
    InMemoryCache implementation.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        Provides the TCK with instances of our InMemoryCache provider.
        """

        async def _factory(**config):
            await asyncio.sleep(0)  # Simulate async operation
            return InMemoryCache()

        return _factory
