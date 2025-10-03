# User Guide: Implementing the Multi-Tenancy Contract (Mixin)

The Multi-Tenancy contract is a **policy mixin**.
It is not a standalone contract but is designed to be combined with a persistence contract (like `BaseTestKVStoreContract` or `BaseTestOutboxStorageContract`) to verify data isolation between tenants.
This is a critical contract for any provider intended for use in a SaaS or multi-tenant environment, as it validates a core requirement of the "Portable Policies & Compliance" pillar.

## Contract Overview

**TCK Mixin Class:** ```tck_py.policies.multi_tenancy.TestMultiTenancyContractMixin```

The `TestMultiTenancyContractMixin` contains a suite of tests that verify that operations performed within the context of one tenant do not affect or leak data into another tenant's context.

## How to Use a Mixin Contract

To use this mixin, your compliance test class must inherit from **both** the primitive contract and the mixin contract.
```admonition tip
By inheriting from multiple TCK classes, your test suite automatically gains all tests from all parent classes.
This is a powerful composition pattern.
```

The primary change you will need to make is to your `provider_factory` fixture, which must now satisfy the requirements of both contracts.

### Example Fixture Implementation

Let's look at the example of a `TenantAwareKVStore`. The test class inherits from `BaseTestKVStoreContract` AND `TestMultiTenancyContractMixin`.
```python
# tests/compliance/test_tenant_aware_kv_compliance.py
import pytest
from tck_py.primitives.kv_store import BaseTestKVStoreContract
from tck_py.policies.multi_tenancy import TestMultiTenancyContractMixin
from my_project.providers.my_tenant_aware_kv_store import MyTenantAwareKVStore

class TestMyTenantAwareKVStoreCompliance(BaseTestKVStoreContract, TestMultiTenancyContractMixin):
    """
    This class will automatically run all tests from the KVStore contract
    AND all data isolation tests from the multi-tenancy mixin.
    """

    @pytest.fixture
    def provider_factory(self):
        """
        This factory must now accept a `tenant_id` to satisfy the
        TestMultiTenancyContractMixin's requirements.
        """
        async def _factory(tenant_id: str | None = None, **config):
            # Your provider must be designed to accept a tenant_id
            # during initialization to scope its operations.
            return MyTenantAwareKVStore(tenant_id=tenant_id, **config)

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `TestMultiTenancyContractMixin` and will be run against your provider.

---

### `test_data_is_isolated_between_tenants`

-   **Purpose**: **This is the core test of the contract.** It verifies that tenant data is strictly separated.
-   **Behavior**: The test creates two provider instances, one for `tenant-a` and one for `tenant-b`.
It then writes a value to the **same key** in both tenants.
-   **Requirement**: When reading the key back from each provider, the provider for `tenant-a` **must** only see the value written by `tenant-a`, and the provider for `tenant-b` **must** only see the value written by `tenant-b`.
Any data leakage is a contract violation.

---

### `test_delete_is_isolated_to_tenant`

-   **Purpose**: Ensures that a delete operation in one tenant's context does not affect another tenant's data.
-   **Behavior**: The test writes data to the same key for both `tenant-a` and `tenant-b`.
It then calls `delete()` using only the `tenant-a` provider.
-   **Requirement**: After the delete operation, a `get()` from the `tenant-a` provider must return `None`, while a `get()` from the `tenant-b` provider **must** still return the original value, proving the delete operation was correctly scoped.
