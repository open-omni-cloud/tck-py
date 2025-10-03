# tests/reference/primitives/test_in_memory_secrets.py
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.primitives.secrets import BaseTestSecretsContract
from tck_py.shared.exceptions import SecretNotFoundError

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemorySecrets:
    """
    In-memory implementation of the SecretsProtocol.
    """

    def __init__(self, secrets: dict = None):
        self._secrets = secrets or {}

    async def get(self, secret_name: str) -> str | None:
        if secret_name not in self._secrets:
            await asyncio.sleep(0)  # Changed from pytest.sleep(0)
            raise SecretNotFoundError(f"Secret '{secret_name}' not found.")
        return self._secrets.get(secret_name)


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemorySecretsCompliance(BaseTestSecretsContract):
    """
    Runs the full Secrets TCK compliance suite against the InMemorySecrets
    implementation.
    """

    @pytest.fixture
    def pre_configured_secret_name(self) -> str:
        return "tck/secrets/my-secret"

    @pytest.fixture
    def pre_configured_secret_value(self) -> str:
        return "super-secret-tck-value"

    @pytest.fixture
    def provider_factory(
        self, pre_configured_secret_name, pre_configured_secret_value
    ) -> Callable[..., Awaitable[Any]]:
        """
        Provides the TCK with instances of our InMemorySecrets provider.
        It pre-populates the provider with the secret defined in the TCK.
        """

        async def _factory(**config):
            initial_secrets = {pre_configured_secret_name: pre_configured_secret_value}
            await asyncio.sleep(0)  # Changed from pytest.sleep(0)
            return InMemorySecrets(secrets=initial_secrets)

        return _factory
