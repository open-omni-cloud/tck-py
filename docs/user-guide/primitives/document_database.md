# User Guide: Implementing the Document Database Contract

The Document Database contract provides a standard, low-level interface for providers that interact with document-oriented databases like MongoDB, DynamoDB (in document mode), or Couchbase.
This TCK serves as a foundational layer, ensuring that different document databases can be used interchangeably for basic CRUD (Create, Read, Update, Delete) operations.
More complex repositories (like the Outbox or Saga repositories) can be built on top of a compliant provider.

## Contract Overview

**TCK Class:** ```tck_py.primitives.document_database.BaseTestDocumentDatabaseContract```

The `BaseTestDocumentDatabaseContract` validates the fundamental `insert_one`, `find_one`, `update_one`, `delete_one`, and `find_many` operations.
A key focus is on test isolation, ensuring that tests do not interfere with one another.

## Implementing the Fixture: `provider_factory`

Your fixture must provide a clean database environment for each test.

```admonition danger
Test isolation is critical.
The factory must provide a tuple containing:
1.  A **provider instance** ready to use.
2.  An **async `cleanup_func(collection_name)`** that the TCK will call after each test to delete all documents created during the test run.
```

### Example Fixture Implementation

```python
# tests/compliance/test_mongo_db_compliance.py
import pytest
from tck_py.primitives.document_database import BaseTestDocumentDatabaseContract
from my_project.db.mongo_client import MyMongoClient

@pytest.fixture
async def test_mongo_db():
    # Connect to a test DB
    client = ...
    db = client["test_db"]
    yield db
    # Global teardown if needed
    client.close()

class TestMongoDbCompliance(BaseTestDocumentDatabaseContract):

    @pytest.fixture
    def provider_factory(self, test_mongo_db):
        """
        Provides a MongoDB client and a cleanup function.
        """
        async def _factory(**config):
            provider = MyMongoClient(database=test_mongo_db)

            async def cleanup_func(collection_name: str):
                await test_mongo_db[collection_name].delete_many({})

            return provider, cleanup_func

        return _factory
```

## Contract Test Breakdown

---

### `test_insert_one_and_find_one`

-   **Purpose**: Verifies the basic write and read path.
-   **Behavior**: The test inserts a new document into a unique test collection and immediately tries to retrieve it using `find_one` with a filter matching its unique ID.
It asserts that the retrieved document is identical to the one inserted.
---

### `test_update_one_modifies_document`

-   **Purpose**: Validates the in-place update functionality.
-   **Behavior**: Inserts a document, then calls `update_one` with a filter and an update specification (e.g., using `$set`).
It retrieves the document again and asserts that the specified fields have been modified.
---

### `test_delete_one_removes_document`

-   **Purpose**: Verifies that documents can be successfully removed.
-   **Behavior**: Inserts a document, verifies it exists, calls `delete_one`, and then verifies that a `find_one` for that document now returns `None`.
---

### `test_find_many_returns_multiple_documents`

-   **Purpose**: Validates querying for a set of documents.
-   **Behavior**: The test inserts several documents, some of which match a specific filter (e.g., they share a common `tag`).
It then calls `find_many` with that filter and asserts that the correct number of documents is returned.
