# tests/reference/security/test_in_memory_iam.py
import asyncio  # Keep the async import clean
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.security.iam import BaseTestIAMContract

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemoryIAMProvider:
    """
    A simple in-memory policy evaluator for TCK compliance.
    This implementation prioritizes DENY over ALLOW for overlapping policies.
    """

    def __init__(self, policy_set: list[dict]):
        # Structure: {'allow': [policies], 'deny': [policies]}
        self._policies = {"allow": [], "deny": []}
        for policy in policy_set:
            self._policies[policy["effect"]].append(policy)

    def _matches(
        self, policy: dict, principal: str, action: str, resource: str | None
    ) -> bool:
        """Helper to check if a policy matches the request context."""

        # Principal must always match exactly
        if policy["principal"] != principal:
            return False

        # Action matching (supports simple wildcard *)
        policy_action = policy["action"]
        if policy_action != "*" and (
            policy_action[-1] == "*" and not action.startswith(policy_action[:-1])
        ):
            return False
        if (
            policy_action != "*"
            and policy_action[-1] != "*"
            and policy_action != action
        ):
            return False

        # Resource matching (supports simple wildcard *)
        policy_resource = policy["resource"]

        # If the request has NO resource (None), it should generally
        # fail resource-specific policies.
        if resource is None:
            # Only match if the policy resource is
            # ALSO None (not supported by the input policy structure)
            # OR if the policy resource is intentionally empty (""),
            # OR if the action itself is non-resource specific
            # (handled implicitly by requiring no policy match)
            # For the TCK, a wildcard "*" or any specific resource "store:orders"
            # should NOT match resource=None.
            return False

        # From here, we know 'resource' is a string. We compare it to 'policy_resource'.

        if policy_resource == "*":
            return True

        if (
            policy_resource != "*"
            and policy_resource[-1] == "*"
            and resource.startswith(policy_resource[:-1])
        ):
            return True

        if (
            policy_resource != "*"
            and policy_resource[-1] != "*"
            and policy_resource == resource
        ):
            return True

        return False

    async def is_allowed(
        self, principal: str, action: str, resource: str | None
    ) -> bool:
        # 1. Check for explicit Deny matches (Deny overrides Allow)
        for deny_policy in self._policies["deny"]:
            if self._matches(deny_policy, principal, action, resource):
                return False

        # 2. Check for explicit Allow matches
        for allow_policy in self._policies["allow"]:
            if self._matches(allow_policy, principal, action, resource):
                return True

        await asyncio.sleep(0)  # Simulate async operation

        # 3. Secure-by-default: If no Allow policy is found, deny access.
        return False


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryIAMCompliance(BaseTestIAMContract):
    """
    Runs the full IAM TCK compliance suite against the InMemoryIAMProvider.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        Provides the TCK with instances of our InMemoryIAMProvider.
        """

        async def _factory(policy_set: list):
            await asyncio.sleep(0)  # Simulate async operation
            return InMemoryIAMProvider(policy_set=policy_set)

        return _factory
