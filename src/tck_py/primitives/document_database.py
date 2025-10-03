# src/tck_py/primitives/document_database.py
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest


@pytest.mark.asyncio
class BaseTestDocumentDatabaseContract:
    """
    TCK Contract: Defines the compliance test suite for a low-level
    provider implementing the DocumentDatabaseProtocol.

    This contract validates the fundamental CRUD (Create, Read, Update, Delete)
    operations for a document-oriented database.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[tuple[Any, Callable]]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function. This factory, when awaited,
        must return a tuple of two items:

        1. A provider instance to be tested, with methods like `insert_one`,
           `find_one`, `update_one`, `delete_one`, `find_many`.
        2. An async `cleanup_func(collection_name)` that can be called to
           delete all documents from a collection to ensure test isolation.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_insert_one_and_find_one(self, provider_factory):
        """Verifies that a document that is inserted can be found."""
        provider, cleanup = await provider_factory()
        collection = f"tck-collection-{uuid.uuid4()}"
        doc_id = str(uuid.uuid4())
        document = {"_id": doc_id, "data": "my-test-data", "value": 123}

        try:
            await provider.insert_one(collection, document)

            retrieved_doc = await provider.find_one(collection, {"_id": doc_id})

            assert retrieved_doc is not None
            assert retrieved_doc["_id"] == doc_id
            assert retrieved_doc["data"] == "my-test-data"
        finally:
            await cleanup(collection)

    async def test_find_one_non_existent_returns_none(self, provider_factory):
        """Verifies that finding a non-existent document returns None."""
        provider, cleanup = await provider_factory()
        collection = f"tck-collection-{uuid.uuid4()}"

        try:
            retrieved_doc = await provider.find_one(
                collection, {"_id": str(uuid.uuid4())}
            )
            assert retrieved_doc is None
        finally:
            await cleanup(collection)

    async def test_update_one_modifies_document(self, provider_factory):
        """Verifies that an update operation correctly modifies a document."""
        provider, cleanup = await provider_factory()
        collection = f"tck-collection-{uuid.uuid4()}"
        doc_id = str(uuid.uuid4())
        document = {"_id": doc_id, "status": "PENDING", "version": 1}

        try:
            await provider.insert_one(collection, document)

            # Perform the update
            update_spec = {"$set": {"status": "COMPLETED", "version": 2}}
            await provider.update_one(collection, {"_id": doc_id}, update_spec)

            updated_doc = await provider.find_one(collection, {"_id": doc_id})
            assert updated_doc is not None
            assert updated_doc["status"] == "COMPLETED"
            assert updated_doc["version"] == 2
        finally:
            await cleanup(collection)

    async def test_delete_one_removes_document(self, provider_factory):
        """Verifies that a delete operation removes a document."""
        provider, cleanup = await provider_factory()
        collection = f"tck-collection-{uuid.uuid4()}"
        doc_id = str(uuid.uuid4())
        document = {"_id": doc_id, "data": "to-be-deleted"}

        try:
            await provider.insert_one(collection, document)
            assert await provider.find_one(collection, {"_id": doc_id}) is not None

            await provider.delete_one(collection, {"_id": doc_id})

            assert await provider.find_one(collection, {"_id": doc_id}) is None
        finally:
            await cleanup(collection)

    async def test_find_many_returns_multiple_documents(self, provider_factory):
        """Verifies that find_many correctly returns a list of matching documents."""
        provider, cleanup = await provider_factory()
        collection = f"tck-collection-{uuid.uuid4()}"
        tag = f"tag-{uuid.uuid4()}"

        docs = [
            {"_id": str(uuid.uuid4()), "tag": tag, "index": 1},
            {"_id": str(uuid.uuid4()), "tag": tag, "index": 2},
            {"_id": str(uuid.uuid4()), "tag": "other-tag", "index": 3},
        ]

        try:
            for doc in docs:
                await provider.insert_one(collection, doc)

            found_docs = await provider.find_many(collection, {"tag": tag})

            assert isinstance(found_docs, list)
            assert len(found_docs) == 2

            # Verify the correct documents were returned
            found_indices = {doc["index"] for doc in found_docs}
            assert found_indices == {1, 2}
        finally:
            await cleanup(collection)
