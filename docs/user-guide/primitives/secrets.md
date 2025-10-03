# User Guide: Implementing the Secrets Contract

The Secrets contract defines the standard for providers that securely retrieve sensitive information, such as API keys, database credentials, or certificates.
This is a read-only contract focused on reliability and secure-by-default behavior.
This guide details how to implement a compliant secrets provider by satisfying the `BaseTestSecretsContract`.

## Contract Overview

**TCK Class:** ```tck_py.primitives.secrets.BaseTestSecretsContract```

The `BaseTestSecretsContract` validates that a secrets provider can successfully retrieve existing secrets and, crucially, that it fails securely and predictably when a secret does not exist.

## Implementing the Fixture: `provider_factory`

As with other contracts, you must implement the `provider_factory` fixture.
```info
Unlike a KV store where tests can create their own data, secrets management tests rely on a **pre-configured test environment**.
The TCK assumes certain secrets already exist in your test backend (e.g., a test Vault instance or AWS Secrets Manager).
```

### Example Fixture Implementation

Let's assume you are building a `VaultSecretsProvider`.
The TCK needs to know the names and expected values of the secrets you have configured for the test run.
```python
# tests/compliance/test_vault_secrets_compliance.py
import pytest
from tck_py.primitives.secrets import BaseTestSecretsContract
from my_project.providers.vault_secrets import VaultSecretsProvider

# A fixture to connect to a test Vault instance
@pytest.fixture
async def test_vault_client():
    # In a real scenario, you would configure and connect to a
    # test Vault server here. You would also pre-populate it with
    # the test secret 'tck/secrets/my-secret'.
    client = ...
    yield client
    # Teardown logic
    ...

class TestVaultSecretsCompliance(BaseTestSecretsContract):

    @pytest.fixture
    def provider_factory(self, test_vault_client):
        """
        This factory provides the TCK with instances of our VaultSecretsProvider.
        """
        async def _factory(**config):
            return VaultSecretsProvider(client=test_vault_client)

        return _factory

    # You must also override the fixtures for the pre-configured secret
    # to match what you've set up in your test environment.
    @pytest.fixture
    def pre_configured_secret_name(self) -> str:
        return "tck/secrets/my-secret"

    @pytest.fixture
    def pre_configured_secret_value(self) -> str:
        return "super-secret-tck-value"
```

## Contract Test Breakdown

The following tests are defined in `BaseTestSecretsContract` and will be run against your provider.

---

### `test_get_existing_secret`

-   **Purpose**: Verifies the basic functionality of retrieving a secret.
-   **Behavior**: The test calls `await provider.get()` using the `pre_configured_secret_name`.
It asserts that the returned value matches the `pre_configured_secret_value`. Your provider must correctly fetch this value from the backend.
---

### `test_get_non_existent_secret_raises_exception`

-   **Purpose**: This is the most critical security and reliability test in this contract.
It ensures the provider fails securely.
-   **Behavior**: The test calls `await provider.get()` on a randomly generated, non-existent secret name.
-   **Requirement**: Your provider **must** catch its specific backend exception (e.g., `hvac.exceptions.InvalidPath` for Vault, or a `ResourceNotFoundException` from AWS) and re-raise it as the TCK's standardized ```tck_py.shared.exceptions.SecretNotFoundError```.
Returning `None` is a contract violation.

---

### `test_repeated_get_secret_is_consistent`

-   **Purpose**: Ensures predictable behavior, especially for providers that might implement a cache.
-   **Behavior**: The test calls `await provider.get()` for the same secret twice in a row.
It asserts that the value returned is identical in both calls.
