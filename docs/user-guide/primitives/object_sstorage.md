# User Guide: Implementing the Object Storage Contract

The Object Storage contract provides the standard interface for providers that handle the storage and retrieval of binary data, commonly known as "objects" or "blobs." This is essential for storing files, images, backups, or any unstructured binary data.

This guide details how to implement a compliant object storage provider by satisfying the `TestObjectStorageContract`.

## Contract Overview

**TCK Class:** ```tck_py.primitives.object_storage.TestObjectStorageContract```

The `TestObjectStorageContract` validates the fundamental Create, Read, Update, and Delete (CRUD) lifecycle of an object. It ensures that binary data integrity is maintained during `upload` and `download` operations and that the provider behaves predictably, especially in failure scenarios.

## Implementing the Fixture: `provider_factory`

Your primary task is to implement the `provider_factory` fixture. For object storage, it is critical that each test runs in a clean, isolated environment.

```info
The TCK tests create objects with unique names. For a real provider, you should configure it to use a dedicated test bucket or container. It is also highly recommended that your test setup includes a cleanup step after tests are run to delete any created objects.
```

### Example Fixture Implementation

Let's assume you are building a provider for an S3-compatible service, using a dedicated test bucket managed outside the TCK.

```python
# tests/compliance/test_s3_storage_compliance.py
import pytest
from tck_py.primitives.object_storage import TestObjectStorageContract
from my_project.providers.s3_storage import S3StorageProvider

# Fixture to connect to your S3-compatible test service
@pytest.fixture
async def s3_test_client():
    # Setup code to connect to a test S3 service (e.g., MinIO in Docker)
    # This client should be configured to use a specific test bucket.
    client = ...
    yield client
    # Teardown logic can go here, like cleaning up the bucket.
    ...

class TestS3StorageCompliance(TestObjectStorageContract):

    @pytest.fixture
    def provider_factory(self, s3_test_client):
        """
        This factory provides the TCK with instances of our S3StorageProvider.
        """
        async def _factory(**config):
            # Pass the pre-configured client to your provider instance.
            return S3StorageProvider(client=s3_test_client)

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `TestObjectStorageContract` and will be run against your provider.

---

### `test_upload_and_download_object`

-   **Purpose**: Verifies the core `upload` and `download` functionality with binary data.
-   **Behavior**: The test generates a 1KB block of random binary data, calls `await provider.upload(key, data)`, and then immediately calls `await provider.download(key)`. It asserts that the downloaded data is identical to the original binary data.

---

### `test_download_non_existent_object_raises_exception`

-   **Purpose**: Ensures your provider fails predictably when an object is not found.
-   **Behavior**: The test calls `await provider.download()` on a randomly generated, non-existent object key.
-   **Requirement**: Your provider **must** catch its specific backend exception (e.g., a `NoSuchKey` error from S3) and re-raise it as the TCK's standardized ```tck_py.shared.exceptions.ObjectNotFoundError```. Returning `None` or a different exception is a contract violation.

---

### `test_delete_object_removes_it`

-   **Purpose**: Verifies that the `delete` operation permanently removes an object.
-   **Behavior**: The test uploads an object, then calls `await provider.delete()` on its key. It then attempts to download the same key again and asserts that this final call fails by raising an `ObjectNotFoundError`.

---

### `test_delete_is_idempotent`

-   **Purpose**: A critical idempotency test for cleanup and automation scripts.
-   **Behavior**: The test calls `await provider.delete()` on a key that does not exist. The operation **must** complete successfully without raising any exceptions.

---

### `test_upload_overwrites_existing_object`

-   **Purpose**: Validates that uploading to an existing key replaces the old object.
-   **Behavior**: The test uploads an initial block of data, then immediately uploads a new, different block of data to the same key. It then downloads the key and asserts that the content matches the second block of data.

---

### `test_upload_is_idempotent`

-   **Purpose**: Ensures that re-uploading the same file multiple times is a safe operation.
-   **Behavior**: The test calls `await provider.upload(key, data)` multiple times with the exact same arguments. A final download must return the correct data, and the state of the object store should be as if `upload` was only called once.
