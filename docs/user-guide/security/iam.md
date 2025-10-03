# User Guide: Implementing the IAM Contract

The Identity and Access Management (IAM) contract defines a standard, abstract interface for authorization.
It answers the fundamental question: "Is a principal allowed to perform an action on a resource?"
This contract is one of the most challenging to implement, as it requires creating an abstraction layer over a provider-specific policy engine (like AWS IAM, Google IAM, or Open Policy Agent).

## Contract Overview

**TCK Class:** ```tck_py.security.iam.BaseTestIAMContract```

The `BaseTestIAMContract` validates the core logic of a policy evaluation engine.
It does not test user creation or role assignment. Instead, it verifies that your provider correctly interprets a standardized set of policy rules, with a strong emphasis on secure-by-default principles like "deny overrides allow."

## Implementing the Fixture: `provider_factory`

The fixture for this contract is unique.
It must be able to configure your IAM provider with a dynamic set of policies for each test.
```info
The factory must return an **async function** that accepts one argument: `policy_set`.
This `policy_set` is a list of dictionaries representing the rules to be enforced.
The factory, when awaited, must return a provider instance configured with these rules.
```

### Policy Set Structure

The TCK will provide policies in the following format:
```json
[
  {
    "effect": "allow",
    "principal": "user:alice",
    "action": "kv:read",
    "resource": "store:orders"
  },
  {
    "effect": "deny",
    "principal": "user:alice",
    "action": "kv:delete",
    "resource": "store:orders"
  }
]
```

Your implementation is responsible for translating this abstract structure into the native format of your backend (e.g., an OPA Rego policy, a Vault ACL policy, etc.).

### Example Fixture Implementation

Let's assume an `OpaIamProvider` that uses Open Policy Agent for evaluation.
```python
# tests/compliance/test_opa_iam_compliance.py
import pytest
from tck_py.security.iam import BaseTestIAMContract
from my_project.providers.opa_iam import OpaIamProvider

class TestOpaIamCompliance(BaseTestIAMContract):

    @pytest.fixture
    def provider_factory(self):
        """
        Provides the TCK with instances of our OpaIamProvider, configured
        with the policies provided by the test.
        """
        async def _factory(policy_set: list):
            # Logic to take the TCK's abstract policy set,
            # translate it into a Rego policy, and initialize
            # the OPA engine with it.
            engine = configure_opa_engine(policy_set)
            return OpaIamProvider(engine=engine)

        return _factory
```

## Contract Test Breakdown

The following tests are defined in `BaseTestIAMContract` and will be run against your provider.

---

### `test_explicit_allow`

-   **Purpose**: Verifies that a simple `allow` rule works as expected.
-   **Behavior**: The TCK provides a policy allowing `user:alice` to perform `kv:read`.
It then calls `await provider.is_allowed("user:alice", "kv:read", ...)` and asserts the result is `True`.
---

### `test_secure_by_default_deny`

-   **Purpose**: Ensures your provider is secure by default.
-   **Behavior**: The TCK calls your factory with an **empty policy set**. It then checks a random permission.
-   **Requirement**: In the absence of any `allow` rules, your provider **must** return `False`.
---

### `test_secure_by_default_deny_if_resource_not_specified` (NEW)

-   **Purpose**: Ensures resources are mandatory unless explicitly not needed, preventing broad, accidental access.
-   **Behavior**: The TCK provides a policy allowing access to a wildcard resource (`resource: "*"`) but requests access without providing a resource (`resource=None`).
-   **Requirement**: The provider **must** return `False`, adhering to the principle that a missing resource context defaults to denial, even if a broad policy exists.

---

### `test_deny_overrides_allow`

-   **Purpose**: **This is a critical security test.** It validates that your policy engine correctly gives precedence to `deny` rules.
-   **Behavior**: The TCK provides a broad `allow` rule (e.g., `action: "db:*"`) and a specific `deny` rule (e.g., `action: "db:delete"`).
It then checks both a permitted action (`db:read`) and a denied action (`db:delete`).
-   **Requirement**: The provider must return `True` for the read action but `False` for the delete action, proving the `deny` rule correctly overrode the `allow` rule.
---

### `test_wildcard_in_action`

-   **Purpose**: Verifies support for wildcards, which are essential for writing flexible policies.
-   **Behavior**: The test provides a policy with a wildcard (e.g., `action: "s3:Get*"`).
It then checks against multiple actions, asserting that `s3:GetObject` is allowed but `s3:PutObject` is not.
