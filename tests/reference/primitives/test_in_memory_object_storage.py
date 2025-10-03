# tests/reference/primitives/test_in_memory_object_storage.py
import asyncio  # New Import
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.primitives.object_storage import (
    BaseTestObjectStorageContract,
)

# Changed from TestObjectStorageContract
from tck_py.shared.exceptions import ObjectNotFoundError

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemoryObjectStorage:
    """
    In-memory implementation of the ObjectStorageProtocol.
    It stores binary data in a dictionary.
    """

    def __init__(self):
        self._data: dict[str, bytes] = {}

    async def upload(self, object_key: str, data: bytes):
        await asyncio.sleep(0)  # Changed from pytest.sleep(0)
        self._data[object_key] = data

    async def download(self, object_key: str) -> bytes | None:
        if object_key not in self._data:
            await asyncio.sleep(0)  # Changed from pytest.sleep(0)
            raise ObjectNotFoundError(f"Object '{object_key}' not found.")
        return self._data.get(object_key)

    async def delete(self, object_key: str):
        await asyncio.sleep(0)  # Changed from pytest.sleep(0)
        self._data.pop(object_key, None)


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryObjectStorageCompliance(BaseTestObjectStorageContract):
    """
    Runs the full Object Storage TCK compliance suite against the
    InMemoryObjectStorage implementation.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        Provides the TCK with instances of our InMemoryObjectStorage provider.
        """

        async def _factory(**config):
            await asyncio.sleep(0)  # Changed from pytest.sleep(0)
            return InMemoryObjectStorage()

        return _factory
