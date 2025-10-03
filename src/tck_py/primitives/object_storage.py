# src/tck_py/primitives/object_storage.py
import os
import uuid

import pytest

from tck_py.shared.exceptions import ObjectNotFoundError


@pytest.mark.asyncio
class BaseTestObjectStorageContract:
    """
    TCK Contract: Defines the compliance test suite for any provider
    implementing the ObjectStorageProtocol.
    To use this TCK, a concrete test class must inherit from this one
    and implement the `provider_factory` fixture.
    """

    @pytest.fixture
    def provider_factory(self):
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return a factory function that, when called,
        returns a new instance of the object storage provider to be tested.
        The returned provider should be an awaitable async object.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_upload_and_download_object(self, provider_factory):
        """
        Verifies that binary data that has been uploaded can be correctly downloaded.
        """
        provider = await provider_factory()

        object_key = f"tck-test-object-{uuid.uuid4()}.bin"
        original_data = os.urandom(1024)  # 1KB of random binary data

        await provider.upload(object_key, original_data)

        downloaded_data = await provider.download(object_key)

        assert downloaded_data is not None
        assert downloaded_data == original_data

    async def test_download_non_existent_object_raises_exception(
        self, provider_factory
    ):
        """
        Verifies that attempting to download a non-existent object raises a
        standardized ObjectNotFoundError.
        """
        provider = await provider_factory()

        non_existent_key = f"tck-non-existent-{uuid.uuid4()}.bin"

        with pytest.raises(ObjectNotFoundError):
            await provider.download(non_existent_key)

    async def test_delete_object_removes_it(self, provider_factory):
        """
        Verifies that after deleting an object, a subsequent download fails.
        """
        provider = await provider_factory()

        object_key = f"tck-to-be-deleted-{uuid.uuid4()}.bin"
        data = os.urandom(128)

        await provider.upload(object_key, data)

        # Now, delete the object
        await provider.delete(object_key)

        # A subsequent download should fail
        with pytest.raises(ObjectNotFoundError):
            await provider.download(object_key)

    async def test_delete_is_idempotent(self, provider_factory):
        """
        Verifies that deleting a non-existent object does not raise an error.
        """
        provider = await provider_factory()

        non_existent_key = f"tck-non-existent-{uuid.uuid4()}.bin"

        try:
            await provider.delete(non_existent_key)
        except Exception as e:
            pytest.fail(
                f"Deleting a non-existent object raised an unexpected exception: {e}"
            )

    async def test_upload_overwrites_existing_object(self, provider_factory):
        """
        Verifies that uploading to an existing object key overwrites the content.
        """
        provider = await provider_factory()

        object_key = f"tck-overwrite-test-{uuid.uuid4()}.bin"
        initial_data = os.urandom(256)
        overwritten_data = os.urandom(512)

        await provider.upload(object_key, initial_data)
        assert await provider.download(object_key) == initial_data

        await provider.upload(object_key, overwritten_data)
        downloaded_data = await provider.download(object_key)

        assert downloaded_data == overwritten_data
        assert downloaded_data != initial_data

    async def test_upload_is_idempotent(self, provider_factory):
        """
        Verifies that calling upload() multiple times with the same key and
        data results in the same final state as calling it once.
        """
        provider = await provider_factory()

        object_key = f"tck-idempotent-object-{uuid.uuid4()}.bin"
        original_data = os.urandom(512)

        # Call upload multiple times
        await provider.upload(object_key, original_data)
        await provider.upload(object_key, original_data)
        await provider.upload(object_key, original_data)

        downloaded_data = await provider.download(object_key)

        assert downloaded_data == original_data
