# tests/reference/resilience/test_in_memory_circuit_breaker.py
import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.resilience.circuit_breaker import BaseTestCircuitBreakerContract
from tck_py.shared.exceptions import CircuitOpenError
from tck_py.shared.models import CircuitState

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemoryCircuitBreaker:
    """
    A simple in-memory implementation of the Circuit Breaker pattern state machine.
    """

    def __init__(self, failure_threshold: int, reset_timeout: float):
        self._threshold = failure_threshold
        self._timeout = reset_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._open_time = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        # Check for transition from OPEN to HALF_OPEN based on time
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() >= self._open_time + self._timeout
        ):
            self._state = CircuitState.HALF_OPEN
        return self._state

    async def execute(self, operation: Callable[..., Awaitable[Any]], *args, **kwargs):
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                raise CircuitOpenError("Circuit is OPEN. Execution blocked.")

            # Note: No state change here. Execution begins in HALF_OPEN.
            # Success/failure will determine the next state (CLOSED or OPEN).

            try:
                result = await operation(*args, **kwargs)

                # If successful: reset if currently HALF_OPEN or CLOSED
                if (
                    current_state == CircuitState.HALF_OPEN
                    or current_state == CircuitState.CLOSED
                ):
                    self._reset()

                return result
            except Exception as e:
                self._record_failure()
                raise e

    def _record_failure(self):
        self._failure_count += 1

        if (self._state == CircuitState.HALF_OPEN) or (
            self._state == CircuitState.CLOSED
            and self._failure_count >= self._threshold
        ):
            # Either trial call failed in HALF_OPEN, or threshold reached in CLOSED
            self._open_circuit()

    def _open_circuit(self):
        self._state = CircuitState.OPEN
        self._open_time = time.monotonic()
        # Note: _failure_count is ONLY reset on transition to CLOSED (_reset method)

    def _reset(self):
        self._state = CircuitState.CLOSED
        self._failure_count = 0


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemoryCircuitBreakerCompliance(BaseTestCircuitBreakerContract):
    """
    Runs the full Circuit Breaker TCK compliance suite against the
    InMemoryCircuitBreaker implementation.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        Provides the TCK with configured instances of our Circuit Breaker.
        """

        async def _factory(failure_threshold: int, reset_timeout: float):
            await asyncio.sleep(0)  # Simulate async operation
            return InMemoryCircuitBreaker(
                failure_threshold=failure_threshold, reset_timeout=reset_timeout
            )

        return _factory
