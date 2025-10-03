# tests/reference/primitives/test_in_memory_kv_store.py
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.primitives.kv_store import (
    BaseTestKVStoreContract,
)

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemoryKVStore:
    """
    A simple, non-production-ready, in-memory implementation of the
    KVStoreProtocol.
    Its purpose is to validate the TCK and serve as a
    reference for other developers.
    """

    def __init__(self):
        self._data = {}

    async def get(self, key: str) -> str | None:
        await asyncio.sleep(0)  # Changed from pytest.sleep(0)
        return self._data.get(key)

    async def set(self, key: str, value: str):
        await asyncio.sleep(0)  # Changed from pytest.sleep(0)
        self._data[key] = value

    async def delete(self, key: str):
        await asyncio.sleep(0)  # Changed from pytest.sleep(0)
        self._data.pop(key, None)


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryKVStoreCompliance(BaseTestKVStoreContract):
    """
    This test class runs the full KVStore TCK compliance suite against
    our InMemoryKVStore implementation.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        This fixture provides the TCK with instances of our InMemoryKVStore.
        """

        async def _factory(**config):
            await asyncio.sleep(0)  # Changed from pytest.sleep(0)
            return InMemoryKVStore()

        return _factory
