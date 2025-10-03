# Getting Started: Certifying Your First Provider

This guide provides a step-by-step tutorial on how to use the Open Omni-Cloud TCK to test and certify a new provider implementation.
We will build a simple, in-memory Key-Value store provider and run the `BaseTestKVStoreContract` compliance suite against it.

## The Core Concepts

Before we start, it's important to understand three core concepts:

1.  **Protocol**: This is the interface contract that your provider must implement.
It's a standard Python `Protocol` defining the required methods and their signatures. The TCK does not provide these;
your framework (like Fortify) does.

2.  **TCK Contract Class**: This is a `pytest`-based class provided by this TCK library (e.g., `BaseTestKVStoreContract`).
It contains all the abstract tests for a specific protocol. Your test class will inherit from this.
3.  **Fixture (`provider_factory`)**: This is the "glue". It's a `pytest` fixture that you must implement in your test class.
Its job is to tell the TCK how to get an instance of *your* provider so the tests can run against it.
## Step 1: Install Dependencies

In your Python project, add `pytest`, `pytest-asyncio`, and the TCK as development dependencies.
```bash
poetry add --group dev open-omni-cloud-tck pytest pytest-asyncio
```

## Step 2: Implement Your Provider

Create your provider class.
For this tutorial, we will create a simple in-memory provider that aims to be compliant with a hypothetical `KVStoreProtocol`.
```python
# your_project/providers/in_memory_kv.py

class InMemoryKVStore:
    """A simple in-memory implementation of the KVStoreProtocol."""
    def __init__(self):
        self._data = {}
        print("Provider Initialized!")

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str):
        self._data[key] = value

    async def delete(self, key: str):
        self._data.pop(key, None)

    async def some_operation(self):
        """A generic method for observability tests."""
        print("Performing some operation...")

    async def some_operation_that_logs(self, message: str):
        """A generic method for logging tests."""
        print(f"Logging: {message}")
```

## Step 3: Create the Compliance Test File

This is the core of the process.
In your `tests/` directory, create a test file that uses the TCK.
1.  Import the relevant contract class from the TCK (e.g., `BaseTestKVStoreContract`).
2.  Import your provider implementation (`InMemoryKVStore`).
3.  Create a test class that inherits from the TCK contract class.
4.  Implement the mandatory `provider_factory` fixture inside your class.
```python
# your_project/tests/compliance/test_in_memory_kv_compliance.py
import pytest
from tck_py.primitives.kv_store import BaseTestKVStoreContract
from your_project.providers.in_memory_kv import InMemoryKVStore

# Inherit from the TCK contract class
class TestInMemoryKVStoreCompliance(BaseTestKVStoreContract):
    """
    This class runs the full TCK compliance suite against our InMemoryKVStore.
    """

    # The only thing we need to do is implement the required fixture.
    @pytest.fixture
    def provider_factory(self):
        """
        This fixture tells the TCK how to get an instance of the
        provider we want to test.
        """
        async def _factory(**config):
            # Logic to instantiate and return our provider.
            # For a real provider (e.g., Redis), you might connect to a
            # test instance (like a Docker container) here.
            return InMemoryKVStore()

        return _factory
```

## Step 4: Run the Tests and Interpret the Results

Now, run `pytest` from your project's root directory.
```bash
poetry run pytest
```

You will see `pytest` discover and run all the tests defined inside `BaseTestKVStoreContract`.
-   **If all tests pass**: Congratulations! Your provider is compliant with the `KVStore` contract of the Open Omni-Cloud standard.
-   **If any test fails**: The output will show you exactly which part of the contract your provider is violating (e.g., "failed on `test_delete_is_idempotent`").
You can then debug your implementation until it passes the full suite.
This process ensures that any provider passing the TCK behaves in a predictable, standardized way, making it a true interchangeable component in the Open Omni-Cloud ecosystem.
