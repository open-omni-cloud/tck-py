# Open Omni-Cloud TCK for Python

[![PyPI](https://img.shields.io/pypi/v/open-omni-cloud-tck.svg)](https://pypi.org/project/open-omni-cloud-tck/)
[![CI/CD](https://github.com/open-omni-cloud/tck-py/actions/workflows/ci.yml/badge.svg)](https://github.com/open-omni-cloud/tck-py/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

The official Technology Compatibility Kit (TCK) for Python implementations of the Open Omni-Cloud standard.
## The Problem: The Broken Multi-Cloud Promise

Most "multi-cloud" strategies fail to deliver true portability, resulting in higher operational complexity and a disguised form of vendor lock-in.
The industry lacks a verifiable, engineering-first definition for what "omni-cloud" means.
The Open Omni-Cloud standard aims to fix this by replacing marketing ambiguity with a testable contract for our infrastructure dependencies.
This TCK is the tool that enforces that contract.

## What is the Open Omni-Cloud TCK?
This is a `pytest`-based test suite designed to certify that a provider implementation (e.g., a wrapper for AWS SQS, Google Cloud Storage, or HashiCorp Vault) complies with the behavior and API contracts defined by the Open Omni-Cloud standard.
A provider that passes this TCK is certified as a **drop-in replacement** for any other compliant provider, finally delivering on the promise of a truly cloud-agnostic architecture.
## Getting Started: Certifying Your Provider

This guide will walk you through using the TCK to test a new provider.
Let's assume you are building a new in-memory `KVStore` provider.
### 1. Installation

First, add `open-omni-cloud-tck` (once it's published) and its dependencies to your project's development environment.
```bash
poetry add --group dev open-omni-cloud-tck pytest pytest-asyncio
```

### 2. Implement the Provider Protocol

Your provider must implement the corresponding protocol.
For this example, we'll assume a `KVStoreProtocol` exists.

```python
# your_project/providers/in_memory_kv.py

class InMemoryKVStore:
    """A simple in-memory implementation of the KVStoreProtocol."""
    def __init__(self):
        self._data = {}

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str):
        self._data[key] = value

    async def delete(self, key: str):
        self._data.pop(key, None)
```

### 3. Create the TCK Test File

In your project's test suite, create a new test file that inherits from the corresponding TCK contract class.
```python
# your_project/tests/integration/test_in_memory_kv_compliance.py
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
            # Logic to instantiate and return our provider
            return InMemoryKVStore()

        return _factory
```

### 4. Run the Tests

Now, simply run `pytest`.
```bash
poetry run pytest
```

`pytest` will discover `TestInMemoryKVStoreCompliance`, see that it inherits all the tests from `BaseTestKVStoreContract`, and automatically run the entire compliance suite against your implementation.
If all tests pass, your provider is certified as Open Omni-Cloud compliant for the KVStore contract.
## Project Structure

The TCK is organized into modules that mirror the high-level architectural concepts of the Open Omni-Cloud standard.
This modular structure separates contracts by their architectural purpose.

-   `tck_py/shared/`: Contains shared code used across the TCK, such as canonical `models` and standardized `exceptions`.
-   `tck_py/primitives/`: Contains contracts for fundamental, atomic infrastructure blocks.
These are the basic building blocks for any cloud-native application.
-   `kv_store.py`
    -   `secrets.py`
    -   `object_storage.py`
    -   `cache.py`
    -   `document_database.py`

-   `tck_py/messaging/`: A complex domain with contracts for its constituent parts.
-   `producer.py`
    -   `consumer.py`
    -   `delayed_messaging.py`

-   `tck_py/resilience/`: Contracts for high-level resilience patterns that ensure system stability.
-   `transactional_outbox.py`
    -   `sagas.py`
    -   `distributed_lock.py`
    -   `circuit_breaker.py`

-   `tck_py/observability/`: Contracts for cross-cutting concerns that ensure any compliant provider is monitorable by default.
-   `tracing.py`
    -   `metrics.py`
    -   `logging.py`

-   `tck_py/policies/`: Contains "Mixin" contracts for cross-cutting policies like data isolation.
-   `multi_tenancy.py`

-   `tck_py/security/`: Contracts related to authentication and authorization.
-   `iam.py`

### Advanced Usage: Testing with Policy Mixins

The TCK uses "mixin" contracts for cross-cutting concerns like multi-tenancy.
You can combine a primitive contract with a policy mixin to create a comprehensive compliance suite for a provider that supports both.
This pattern allows for powerful and reusable test composition.

**Example: Certifying a Tenant-Aware KVStore Provider**

1.  **Define your Test Class inheriting from both contracts:**

    Your test class should inherit from the primitive contract (`BaseTestKVStoreContract`) and the policy mixin (`TestMultiTenancyContractMixin`).
2.  **Implement the combined Fixture:**

    Your `provider_factory` fixture must now satisfy the requirements of *both* contracts.
Specifically, it must accept the `tenant_id` argument required by the multi-tenancy mixin.
```python
# your_project/tests/integration/test_tenant_aware_kv_compliance.py
import pytest
from tck_py.primitives.kv_store import BaseTestKVStoreContract
from tck_py.policies.multi_tenancy import TestMultiTenancyContractMixin

# A placeholder for your provider that is tenant-aware
class MyTenantAwareKVStore:
    def __init__(self, tenant_id: str | None = None):
        # A real implementation would use the tenant_id to scope data
        self._tenant_id = tenant_id
        # ...

# Inherit from BOTH the primitive contract and the policy mixin
class TestMyTenantAwareProviderCompliance(BaseTestKVStoreContract, TestMultiTenancyContractMixin):
    """
    This class will automatically run all tests from the KVStore contract AND
    all data isolation tests from the multi-tenancy mixin.
    """

    @pytest.fixture
    def provider_factory(self):
        """
        This factory now implements the combined requirements, including the
        `tenant_id` parameter needed by the TestMultiTenancyContractMixin.
        """
        async def _factory(tenant_id: str | None = None, **config):
            # Logic to instantiate the provider, passing the tenant_id to it
            return MyTenantAwareKVStore(tenant_id=tenant_id, **config)

        return _factory
```

By inheriting from both classes, `TestMyTenantAwareProviderCompliance` will automatically discover and run all tests for a basic KV store **and** all data isolation tests for multi-tenancy, ensuring complete compliance with a single,
declarative test class.


## Contributing

Contributions are welcome! This project is in its early stages, and we are actively looking for feedback and contributors to help shape the future of cloud-agnostic computing. Please see our `CONTRIBUTING.md` file for more details.

## License

This project is licensed under the **Apache 2.0 License**.
