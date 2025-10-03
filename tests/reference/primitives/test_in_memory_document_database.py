# tests/reference/primitives/test_in_memory_document_database.py
import asyncio
import copy
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.primitives.document_database import BaseTestDocumentDatabaseContract

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemoryDocumentDatabase:
    """
    In-memory implementation of the DocumentDatabaseProtocol.

    It uses a dictionary to simulate a database, where top-level keys
    are collection names, and their values are another dictionary
    of documents keyed by their '_id'.
    """

    def __init__(self):
        # Structure: { "collection_name": { "doc_id_1": {...}, "doc_id_2": {...} } }
        self._db: dict[str, dict[str, dict]] = {}

    def _get_collection(self, name: str) -> dict[str, dict]:
        if name not in self._db:
            self._db[name] = {}
        return self._db[name]

    async def insert_one(self, collection: str, document: dict):
        coll = self._get_collection(collection)
        doc_id = document.get("_id", str(uuid.uuid4()))
        document["_id"] = doc_id
        coll[doc_id] = copy.deepcopy(document)
        await asyncio.sleep(0)

    async def find_one(self, collection: str, filter: dict) -> dict | None:
        coll = self._get_collection(collection)
        for _doc_id, doc in coll.items():
            match = all(doc.get(key) == value for key, value in filter.items())
            if match:
                return copy.deepcopy(doc)
        await asyncio.sleep(0)
        return None

    async def find_many(self, collection: str, filter: dict) -> list[dict]:
        coll = self._get_collection(collection)
        results = []
        for _doc_id, doc in coll.items():
            match = all(doc.get(key) == value for key, value in filter.items())
            if match:
                results.append(copy.deepcopy(doc))
        await asyncio.sleep(0)
        return results

    async def update_one(self, collection: str, filter: dict, update_spec: dict):
        coll = self._get_collection(collection)
        doc_to_update = await self.find_one(collection, filter)
        if doc_to_update:
            doc_id = doc_to_update["_id"]
            if "$set" in update_spec:
                for key, value in update_spec["$set"].items():
                    coll[doc_id][key] = value

    async def delete_one(self, collection: str, filter: dict):
        coll = self._get_collection(collection)
        doc_to_delete = await self.find_one(collection, filter)
        if doc_to_delete:
            doc_id = doc_to_delete["_id"]
            if doc_id in coll:
                del coll[doc_id]


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryDocumentDatabaseCompliance(BaseTestDocumentDatabaseContract):
    """
    Runs the full Document Database TCK compliance suite against the
    InMemoryDocumentDatabase implementation.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[tuple[Any, Callable]]]:
        """
        Provides the TCK with an instance of our InMemoryDocumentDatabase
        and a cleanup function.
        """
        # Maintain a single instance for the test session to simulate a real DB
        # But provide a way to clean collections between tests.
        provider = InMemoryDocumentDatabase()

        async def _factory(**config):
            await asyncio.sleep(0)

            async def cleanup_func(collection_name: str):
                if collection_name in provider._db:
                    provider._db[collection_name].clear()

                await asyncio.sleep(0)

            return provider, cleanup_func

        return _factory
