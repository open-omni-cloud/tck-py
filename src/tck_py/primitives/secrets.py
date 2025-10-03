# src/tck_py/primitives/secrets.py
import uuid

import pytest

from tck_py.shared.exceptions import SecretNotFoundError


@pytest.mark.asyncio
class BaseTestSecretsContract:
    """
    TCK Contract: Defines the compliance test suite for any provider
    implementing the SecretsProtocol.
    To use this TCK, a concrete test class must inherit from this one
    and implement the `provider_factory` fixture.
    """

    @pytest.fixture
    def provider_factory(self):
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return a factory function that, when called,
        returns a new instance of the secrets provider to be tested.
        The returned provider should be an awaitable async object.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    @pytest.fixture
    def pre_configured_secret_name(self) -> str:
        """
        Fixture that provides the name of a secret that is expected
        to exist in the test environment.
        """
        # This value should be consistent with what is set up in the test backend.
        return "tck/secrets/my-secret"

    @pytest.fixture
    def pre_configured_secret_value(self) -> str:
        """
        Fixture that provides the expected value for the pre-configured secret.
        """
        return "super-secret-tck-value"

    # --- Start of Contract Tests ---

    async def test_get_existing_secret(
        self,
        provider_factory,
        pre_configured_secret_name: str,
        pre_configured_secret_value: str,
    ):
        """
        Verifies that an existing secret can be retrieved with the correct value.
        """
        provider = await provider_factory()

        retrieved_value = await provider.get(pre_configured_secret_name)

        assert retrieved_value is not None
        assert retrieved_value == pre_configured_secret_value

    async def test_get_non_existent_secret_raises_exception(self, provider_factory):
        """
        Verifies that attempting to retrieve a non-existent secret raises a
        standardized SecretNotFoundError.
        Providers are responsible for catching their specific exceptions (e.g.,
        Vault's InvalidPath, AWS's ResourceNotFoundException) and wrapping
        them in the standardized exception.
        """
        provider = await provider_factory()

        non_existent_key = f"tck/non-existent/{uuid.uuid4()}"

        with pytest.raises(SecretNotFoundError):
            await provider.get(non_existent_key)

    async def test_repeated_get_secret_is_consistent(
        self,
        provider_factory,
        pre_configured_secret_name: str,
        pre_configured_secret_value: str,
    ):
        """
        Verifies that repeated calls to get the same secret return the
        same consistent value. This is important for providers that may
        implement caching.
        """
        provider = await provider_factory()

        first_call_value = await provider.get(pre_configured_secret_name)
        second_call_value = await provider.get(pre_configured_secret_name)

        assert first_call_value == pre_configured_secret_value
        assert second_call_value == first_call_value
