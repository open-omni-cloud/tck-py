# tests/reference/resilience/test_in_memory_sagas.py
import asyncio
import copy
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from tck_py.resilience.sagas import BaseTestSagaStateRepositoryContract
from tck_py.shared.exceptions import SagaStateConflictError
from tck_py.shared.models import SagaState

# =============================================================================
# 1. PROVIDER IMPLEMENTATION
# =============================================================================


class InMemorySagaRepository:
    """
    In-memory implementation of the SagaStateRepositoryProtocol.
    It simulates a saga state store and correctly implements optimistic
    concurrency control using a 'version' field.
    """

    def __init__(self):
        # { saga_id: saga_state_object }
        self._sagas: dict[str, SagaState] = {}
        self._lock = asyncio.Lock()

    async def get_state(self, saga_id: str) -> SagaState | None:
        state = self._sagas.get(saga_id)
        await asyncio.sleep(0)
        return copy.deepcopy(state) if state else None

    async def create_state(self, state: SagaState):
        async with self._lock:
            if state.saga_id in self._sagas:
                # In a real system, this might raise a conflict error as well.
                return

            # On creation, the version is set to 1.
            new_state = state._replace(version=1)
            self._sagas[state.saga_id] = new_state

    async def update_state(self, state: SagaState):
        async with self._lock:
            current_state = self._sagas.get(state.saga_id)

            if not current_state:
                # Should not happen in a real flow, but good practice to handle.
                return

            # This is the optimistic concurrency check.
            if current_state.version != state.version:
                raise SagaStateConflictError(
                    f"Stale saga state for id {state.saga_id}. "
                    f"Expected version {current_state.version}, got {state.version}."
                )

            # If versions match, increment version and save.
            updated_state = state._replace(version=state.version + 1)
            self._sagas[state.saga_id] = updated_state


# =============================================================================
# 2. TCK COMPLIANCE TEST
# =============================================================================


class TestInMemorySagaCompliance(BaseTestSagaStateRepositoryContract):
    """
    Runs the full Saga State Repository TCK compliance suite against the
    in-memory implementation.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        Provides the TCK with instances of our InMemorySagaRepository.
        """

        async def _factory(**config):
            await asyncio.sleep(0)
            return InMemorySagaRepository()

        return _factory
