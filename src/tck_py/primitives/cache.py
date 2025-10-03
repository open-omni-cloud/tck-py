# src/tck_py/primitives/cache.py
import asyncio
import uuid

import pytest


@pytest.mark.asyncio
class BaseTestCacheContract:
    """
    TCK Contract: Defines the compliance test suite for any provider
    implementing the CacheProtocol.
    This contract focuses on the core caching functionalities, especially
    the time-to-live (TTL) expiration logic.
    """

    @pytest.fixture
    def provider_factory(self):
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return a factory function that, when called,
        returns a new, clean instance of the cache provider to be tested.
        The returned provider should be an awaitable async object.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_set_and_get_value_without_ttl(self, provider_factory):
        """
        Verifies that a value set without a TTL persists and can be retrieved.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        value = f"test-value-{uuid.uuid4()}"

        await provider.set(key, value, ttl=None)
        retrieved_value = await provider.get(key)

        assert retrieved_value == value

    async def test_get_non_existent_key_is_a_cache_miss(self, provider_factory):
        """
        Verifies that getting a non-existent key returns None (a cache miss).
        """
        provider = await provider_factory()

        key = f"non-existent-key-{uuid.uuid4()}"
        retrieved_value = await provider.get(key)

        assert retrieved_value is None

    async def test_set_with_ttl_and_get_before_expiry(self, provider_factory):
        """
        Verifies that a value set with a TTL can be retrieved before it expires.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        value = "my-expiring-value"

        await provider.set(key, value, ttl=5)  # 5-second TTL
        retrieved_value = await provider.get(key)

        assert retrieved_value == value

    async def test_key_expires_after_ttl(self, provider_factory):
        """
        This is the most critical test for a cache.
        It verifies that a key is no longer available after its TTL has passed.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        value = "this-will-vanish"

        ttl_seconds = 1
        await provider.set(key, value, ttl=ttl_seconds)

        # Wait for a period slightly longer than the TTL
        await asyncio.sleep(ttl_seconds + 0.1)

        retrieved_value = await provider.get(key)

        assert retrieved_value is None, "The key should have expired and returned None."

    async def test_delete_removes_key_before_expiry(self, provider_factory):
        """
        Verifies that an explicit delete removes a key, even if it has a valid TTL.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        value = "value-to-be-deleted"

        await provider.set(key, value, ttl=10)
        assert await provider.get(key) == value

        await provider.delete(key)
        retrieved_value = await provider.get(key)

        assert retrieved_value is None

    async def test_set_overwrites_existing_value_and_ttl(self, provider_factory):
        """
        Verifies that re-setting a key overwrites both its value and its TTL.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        initial_value = "initial-value"
        overwritten_value = "overwritten-value"

        # Set with a long TTL initially
        await provider.set(key, initial_value, ttl=60)
        assert await provider.get(key) == initial_value

        # Overwrite with a new value and a very short TTL
        await provider.set(key, overwritten_value, ttl=1)
        assert await provider.get(key) == overwritten_value

        # Wait for the new, short TTL to expire
        await asyncio.sleep(1.1)

        assert (
            await provider.get(key) is None
        ), "The key should have expired based on the new TTL."
