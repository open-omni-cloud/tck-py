# src/tck_py/security/iam.py
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

KV_READ_ACTION = "kv:read"


@pytest.mark.asyncio
class BaseTestIAMContract:
    """
    TCK Contract: Defines the compliance test suite for any provider
    implementing the abstract IAMProtocol.
    This contract verifies the core authorization logic: evaluating a set of
    policies to answer the question "is this principal allowed to perform
    this action on this resource?".
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function. This factory must accept
        one argument: `policy_set: List[Dict]`.
        The factory is responsible for configuring and returning an initialized
        IAM provider that will enforce the given policy set.
        The policy_set will be a list of dicts, each with keys:
        - 'effect': 'allow' or 'deny'
        - 'principal': str (e.g., 'user:alice')
        - 'action': str (e.g., 'kv:write')
        - 'resource': str (e.g., 'kv:store:orders')
        Wildcards ('*') should be supported in 'action' and 'resource'.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_explicit_allow(self, provider_factory):
        """Verifies a simple, explicit 'allow' policy is correctly enforced."""

        principal = "user:alice"
        resource = "store:orders"
        action = KV_READ_ACTION

        policy_set = [
            {
                "effect": "allow",
                "principal": principal,
                "action": action,
                "resource": resource,
            }
        ]
        provider = await provider_factory(policy_set=policy_set)

        is_allowed = await provider.is_allowed(principal, action, resource)
        assert is_allowed is True

    async def test_explicit_deny(self, provider_factory):
        """Verifies that an action is denied when no policy matches."""

        principal = "user:alice"
        resource = "store:orders"
        action = KV_READ_ACTION

        policy_set = [
            {
                "effect": "allow",
                "principal": principal,
                "action": action,
                "resource": resource,
            }
        ]
        provider = await provider_factory(policy_set=policy_set)

        # Action does not match
        is_allowed = await provider.is_allowed(principal, "kv:write", resource)
        assert is_allowed is False

    async def test_secure_by_default_deny(self, provider_factory):
        """Verifies that with an empty policy set, all actions are denied."""
        provider = await provider_factory(policy_set=[])

        is_allowed = await provider.is_allowed("user:bob", "any:action", "any:resource")
        assert is_allowed is False

    async def test_secure_by_default_deny_if_resource_not_specified(
        self, provider_factory
    ):
        """
        Verifies that even with a broad 'allow' policy, access is denied
        if the resource is not provided in the policy or the request
        (security by default).
        """
        principal = "user:eve"
        action = KV_READ_ACTION

        policy_set = [
            {
                "effect": "allow",
                "principal": principal,
                "action": action,
                "resource": "*",  # Broad resource wildcard
            }
        ]
        provider = await provider_factory(policy_set=policy_set)

        # Request access without specifying a resource
        is_allowed = await provider.is_allowed(principal, action, None)

        # The implementation must treat a missing resource (None) as a default denial
        assert is_allowed is False

    async def test_deny_overrides_allow(self, provider_factory):
        """
        CRITICAL: Verifies that an explicit 'deny' policy takes precedence
        over an 'allow' policy.
        """

        principal = "user:charlie"
        resource = "table:invoices"

        policy_set = [
            {  # Broad allow
                "effect": "allow",
                "principal": principal,
                "action": "db:*",
                "resource": resource,
            },
            {  # Specific deny
                "effect": "deny",
                "principal": principal,
                "action": "db:delete",
                "resource": resource,
            },
        ]
        provider = await provider_factory(policy_set=policy_set)

        # This should be allowed by the wildcard
        assert await provider.is_allowed(principal, "db:read", resource) is True

        # This should be explicitly denied, overriding the wildcard allow
        assert await provider.is_allowed(principal, "db:delete", resource) is False

    async def test_wildcard_in_action(self, provider_factory):
        """Verifies that a wildcard in the 'action' field is respected."""
        principal = "user:david"
        resource = "bucket:financials"

        policy_set = [
            {
                "effect": "allow",
                "principal": principal,
                "action": "s3:Get*",
                "resource": resource,
            }
        ]
        provider = await provider_factory(policy_set=policy_set)

        assert await provider.is_allowed(principal, "s3:GetObject", resource) is True
        assert await provider.is_allowed(principal, "s3:GetObjectAcl", resource) is True
        assert await provider.is_allowed(principal, "s3:PutObject", resource) is False
