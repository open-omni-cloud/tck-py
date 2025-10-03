# src/tck_py/resilience/circuit_breaker.py
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from tck_py.shared.exceptions import CircuitOpenError
from tck_py.shared.models import CircuitState


@pytest.mark.asyncio
class BaseTestCircuitBreakerContract:
    """
    TCK Contract: Defines the compliance test suite for any provider
    implementing the CircuitBreakerProtocol.
    This contract verifies the state machine transitions (CLOSED, OPEN, HALF_OPEN)
    that are fundamental to the circuit breaker pattern.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function that accepts configuration:
        - `failure_threshold (int)`: Number of failures to open the circuit.
        - `reset_timeout (float)`: Seconds before moving from OPEN to HALF_OPEN.

        The factory, when awaited, returns a circuit breaker provider instance.
        This instance must expose:
        - `execute(callable, ...)`: An async method to run a function.
        - `state`: A property to get the current CircuitState.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Helper function for testing ---
    class CallCounter:
        def __init__(self, fail_times=0):
            self._calls = 0
            self._fail_until = fail_times

        async def operation(self, *args, **kwargs):
            self._calls += 1
            if self._calls <= self._fail_until:
                await asyncio.sleep(0)
                raise ValueError("Operation failed as configured.")
            return "success"

        @property
        def call_count(self):
            return self._calls

    # --- Start of Contract Tests ---

    async def test_initial_state_is_closed(self, provider_factory):
        """Verifies a new circuit breaker starts in the CLOSED state."""
        breaker = await provider_factory(failure_threshold=3, reset_timeout=5.0)
        assert breaker.state == CircuitState.CLOSED

    async def test_executes_successfully_in_closed_state(self, provider_factory):
        """Verifies a successful call executes correctly in the CLOSED state."""
        breaker = await provider_factory(failure_threshold=3, reset_timeout=5.0)
        counter = self.CallCounter()

        result = await breaker.execute(counter.operation)

        assert result == "success"
        assert counter.call_count == 1
        assert breaker.state == CircuitState.CLOSED

    async def test_transitions_to_open_after_failures(self, provider_factory):
        """Verifies the circuit transitions from CLOSED to OPEN
        after reaching the failure threshold."""
        breaker = await provider_factory(failure_threshold=2, reset_timeout=5.0)
        counter = self.CallCounter(fail_times=2)

        # First failure
        with pytest.raises(ValueError):
            await breaker.execute(counter.operation)
        assert breaker.state == CircuitState.CLOSED

        # Second failure should trip the breaker
        with pytest.raises(ValueError):
            await breaker.execute(counter.operation)
        assert breaker.state == CircuitState.OPEN

        # Subsequent call should fail immediately without executing the operation
        with pytest.raises(CircuitOpenError):
            await breaker.execute(counter.operation)

        assert (
            counter.call_count == 2
        ), "The operation should not be called when the circuit is OPEN."

    async def test_transitions_to_half_open_after_timeout(self, provider_factory):
        """Verifies the circuit transitions from OPEN to
        HALF_OPEN after the reset timeout."""
        breaker = await provider_factory(failure_threshold=1, reset_timeout=1.0)
        counter = self.CallCounter(fail_times=1)

        # Trip the breaker to OPEN
        with pytest.raises(ValueError):
            await breaker.execute(counter.operation)
        assert breaker.state == CircuitState.OPEN

        # Wait for the timeout
        await asyncio.sleep(1.1)

        assert breaker.state == CircuitState.HALF_OPEN

    async def test_half_open_to_closed_on_success(self, provider_factory):
        """Verifies the circuit transitions from
        HALF_OPEN to CLOSED after a successful call."""
        breaker = await provider_factory(failure_threshold=1, reset_timeout=1.0)
        counter = self.CallCounter(fail_times=1)

        # Trip to OPEN, then wait to go to HALF_OPEN
        with pytest.raises(ValueError):
            await breaker.execute(counter.operation)
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # The next call will succeed (fail_times=1 is already met)
        result = await breaker.execute(counter.operation)

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    async def test_half_open_to_open_on_failure(self, provider_factory):
        """Verifies the circuit transitions from HALF_OPEN back to OPEN on a failure."""
        breaker = await provider_factory(failure_threshold=1, reset_timeout=1.0)
        counter = self.CallCounter(fail_times=2)  # Will fail twice

        # Trip to OPEN, then wait to go to HALF_OPEN
        with pytest.raises(ValueError):
            await breaker.execute(counter.operation)  # First failure
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # This trial call in HALF_OPEN state will also fail
        with pytest.raises(ValueError):
            await breaker.execute(counter.operation)  # Second failure

        assert breaker.state == CircuitState.OPEN
