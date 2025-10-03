# src/tck_py/primitives/kv_store.py
import uuid

import pytest


@pytest.mark.asyncio
class BaseTestKVStoreContract:
    """
    TCK Contract: Defines the compliance test suite for any provider
    implementing the KVStoreProtocol.
    To use this TCK, a concrete test class must inherit from this one
    and implement the `provider_factory` fixture.
    """

    @pytest.fixture
    def provider_factory(self):
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return a factory function that, when called,
        returns a new, clean instance of the provider to be tested.
        The returned provider should be an awaitable async object if
        it has async methods.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_set_and_get_value(self, provider_factory):
        """
        Verifies that a value that has been set can be correctly retrieved.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        value = f"test-value-{uuid.uuid4()}"

        await provider.set(key, value)
        retrieved_value = await provider.get(key)

        assert retrieved_value == value

    async def test_get_non_existent_key_returns_none(self, provider_factory):
        """
        Verifies that fetching a key that does not exist returns None.
        """
        provider = await provider_factory()

        key = f"non-existent-key-{uuid.uuid4()}"
        retrieved_value = await provider.get(key)

        assert retrieved_value is None

    async def test_set_overwrites_existing_value(self, provider_factory):
        """
        Verifies that setting a value for an existing key overwrites the old value.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        initial_value = "initial-value"
        overwritten_value = "overwritten-value"

        await provider.set(key, initial_value)
        assert await provider.get(key) == initial_value

        await provider.set(key, overwritten_value)
        retrieved_value = await provider.get(key)

        assert retrieved_value == overwritten_value

    async def test_delete_removes_key(self, provider_factory):
        """
        Verifies that after deleting a key, getting it returns None.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        value = "value-to-be-deleted"

        await provider.set(key, value)
        assert await provider.get(key) == value

        await provider.delete(key)
        retrieved_value = await provider.get(key)

        assert retrieved_value is None

    async def test_delete_is_idempotent(self, provider_factory):
        """
        Verifies that deleting a non-existent key does not raise an error
        and the key remains non-existent.
        """
        provider = await provider_factory()

        key = f"non-existent-key-{uuid.uuid4()}"

        # First, ensure the key does not exist
        assert await provider.get(key) is None

        # The delete operation should complete without errors
        try:
            await provider.delete(key)
        except Exception as e:
            pytest.fail(
                f"Deleting a non-existent key raised an unexpected exception: {e}"
            )

        # Finally, ensure the key still does not exist
        assert await provider.get(key) is None

    async def test_set_is_idempotent(self, provider_factory):
        """
        Verifies that calling set() multiple times with the same key and
        value results in the same final state as calling it once.
        """
        provider = await provider_factory()

        key = f"test-key-{uuid.uuid4()}"
        value = f"test-value-{uuid.uuid4()}"

        # Call set multiple times
        await provider.set(key, value)
        await provider.set(key, value)
        await provider.set(key, value)

        retrieved_value = await provider.get(key)
        assert retrieved_value == value

        # Also verify that it doesn't interfere with other keys
        # (This is a sanity check, not strictly idempotency)
        other_key = f"other-key-{uuid.uuid4()}"
        await provider.set(other_key, "other_value")
        assert await provider.get(other_key) == "other_value"
        assert await provider.get(key) == value
