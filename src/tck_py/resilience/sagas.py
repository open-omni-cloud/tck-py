# src/tck_py/resilience/sagas.py
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from tck_py.shared.exceptions import SagaStateConflictError
from tck_py.shared.models import SagaState, SagaStepHistory


@pytest.mark.asyncio
class BaseTestSagaStateRepositoryContract:
    """
    TCK Contract: Defines the compliance test suite for any storage provider
    implementing the SagaStateRepositoryProtocol.
    This contract verifies the correct persistence, retrieval, and crucially,
    the optimistic concurrency control for saga state.
    """

    @pytest.fixture
    def provider_factory(self) -> Callable[..., Awaitable[Any]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function that, when awaited,
        returns a new, clean instance of the saga state repository to be tested.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the 'provider_factory' fixture."
        )

    # --- Start of Contract Tests ---

    async def test_create_and_get_saga_state(self, provider_factory):
        """
        Verifies that a new saga state can be created and then retrieved correctly.
        """
        provider = await provider_factory()
        saga_id = str(uuid.uuid4())
        initial_state = SagaState(
            saga_id=saga_id,
            status="RUNNING",
            current_step=0,
            history=[],
            payload={"initial": True},
            version=0,  # The create method should handle the initial versioning
        )

        await provider.create_state(initial_state)

        retrieved_state = await provider.get_state(saga_id)

        assert retrieved_state is not None
        assert retrieved_state.saga_id == saga_id
        assert retrieved_state.status == "RUNNING"
        assert retrieved_state.payload == {"initial": True}
        assert retrieved_state.version == 1  # Should be set to 1 on creation

    async def test_get_non_existent_saga_returns_none(self, provider_factory):
        """
        Verifies that getting a non-existent saga state returns None.
        """
        provider = await provider_factory()
        saga_id = str(uuid.uuid4())

        retrieved_state = await provider.get_state(saga_id)

        assert retrieved_state is None

    async def test_update_saga_state_increments_version(self, provider_factory):
        """
        Verifies that updating a saga state correctly modifies its data
        and increments the version number.
        """
        provider = await provider_factory()
        saga_id = str(uuid.uuid4())

        # Create initial state
        initial_state = SagaState(
            saga_id=saga_id,
            status="RUNNING",
            current_step=0,
            history=[],
            payload={},
            version=0,
        )
        await provider.create_state(initial_state)

        # First update
        state_v1 = await provider.get_state(saga_id)
        assert state_v1.version == 1

        state_to_update = state_v1._replace(
            current_step=1,
            history=[SagaStepHistory(step_name="step1", status="SUCCESS")],
        )
        await provider.update_state(state_to_update)

        retrieved_state_v2 = await provider.get_state(saga_id)
        assert retrieved_state_v2.version == 2
        assert retrieved_state_v2.current_step == 1
        assert len(retrieved_state_v2.history) == 1

    async def test_update_with_stale_version_raises_conflict_error(
        self, provider_factory
    ):
        """
        This is a critical test for optimistic concurrency control.
        It verifies that attempting to update a saga state using a stale
        version number raises a SagaStateConflictError.
        """
        provider = await provider_factory()
        saga_id = str(uuid.uuid4())

        # Create initial state
        initial_state = SagaState(
            saga_id=saga_id,
            status="RUNNING",
            current_step=0,
            history=[],
            payload={},
            version=0,
        )
        await provider.create_state(initial_state)

        # Both processes load the same version of the state
        process_a_state = await provider.get_state(saga_id)  # the version = 1
        process_b_state = await provider.get_state(saga_id)  # the version = 1

        # Process A successfully updates the state
        process_a_state_update = process_a_state._replace(current_step=1)
        await provider.update_state(process_a_state_update)

        # Now the state in the DB is at version = 2

        # Process B, which holds a stale state (version = 1), tries to update.
        # This attempt MUST fail.
        process_b_state_update = process_b_state._replace(status="FAILED")
        with pytest.raises(SagaStateConflictError):
            await provider.update_state(process_b_state_update)

        # Verify that the stale update from Process B did not go through
        final_state = await provider.get_state(saga_id)
        assert final_state.version == 2
        assert (
            final_state.status == "RUNNING"
        )  # Still the status from Process A's update
        assert final_state.current_step == 1
