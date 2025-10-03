# src/tck_py/policies/multi_tenancy.py
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest


@pytest.mark.asyncio
class TestMultiTenancyContractMixin:
    """
    TCK Contract Mixin: Defines the compliance test suite for data isolation
    in a multi-tenant environment.

    This class is intended to be mixed in with other persistence contracts
    (e.g., TestKVStoreContract, TestOutboxStorageContract).
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        This fixture MUST be implemented by the class that uses this mixin.

        The factory it returns must accept an optional `tenant_id: str`.
        When `tenant_id` is provided, the created provider instance MUST
        operate exclusively within that tenant's data scope.
        """
        raise NotImplementedError(
            "The 'provider_factory' fixture must be implemented and support "
            "a 'tenant_id' argument."
        )

    # --- Start of Contract Tests ---

    async def test_data_is_isolated_between_tenants(self, provider_factory):
        """
        Verifies that data created by one tenant cannot be seen by another,
        even when using the same key.
        """
        tenant_a_id = f"tenant-{uuid.uuid4()}"
        tenant_b_id = f"tenant-{uuid.uuid4()}"

        # Create providers scoped to each tenant
        provider_a = await provider_factory(tenant_id=tenant_a_id)
        provider_b = await provider_factory(tenant_id=tenant_b_id)

        shared_key = "shared-key"
        value_a = f"value-for-a-{uuid.uuid4()}"
        value_b = f"value-for-b-{uuid.uuid4()}"

        # Set data in each tenant using the same key
        await provider_a.set(shared_key, value_a)
        await provider_b.set(shared_key, value_b)

        # Verify that each provider can only see its own data
        assert (
            await provider_a.get(shared_key) == value_a
        ), "Provider A should only see Tenant A's data."
        assert (
            await provider_b.get(shared_key) == value_b
        ), "Provider B should only see Tenant B's data."

    async def test_delete_is_isolated_to_tenant(self, provider_factory):
        """
        Verifies that a delete operation in one tenant does not affect the
        data of another tenant.
        """
        tenant_a_id = f"tenant-{uuid.uuid4()}"
        tenant_b_id = f"tenant-{uuid.uuid4()}"

        provider_a = await provider_factory(tenant_id=tenant_a_id)
        provider_b = await provider_factory(tenant_id=tenant_b_id)

        shared_key = "shared-key-to-delete"
        value_a = "value-a"
        value_b = "value-b"

        await provider_a.set(shared_key, value_a)
        await provider_b.set(shared_key, value_b)

        # Delete the key only in Tenant A's context
        await provider_a.delete(shared_key)

        # Verify Tenant A's data is gone, but Tenant B's remains
        assert (
            await provider_a.get(shared_key) is None
        ), "Data should be deleted for Tenant A."
        assert (
            await provider_b.get(shared_key) == value_b
        ), "Data for Tenant B should not be affected."
