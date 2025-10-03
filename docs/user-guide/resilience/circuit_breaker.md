# User Guide: Implementing the Circuit Breaker Contract

The Circuit Breaker is a core resilience pattern that prevents an application from repeatedly trying to execute an operation that is likely to fail, preventing cascading failures across a distributed system.
This guide details how to implement a compliant Circuit Breaker provider by satisfying the `BaseTestCircuitBreakerContract`.

## Contract Overview

**TCK Class:** ```tck_py.resilience.circuit_breaker.BaseTestCircuitBreakerContract```

The `BaseTestCircuitBreakerContract` validates the Circuit Breaker's state machine.
It ensures the provider correctly transitions between its three states—**CLOSED**, **OPEN**, and **HALF_OPEN**—based on the success or failure of the operations it protects.

## Implementing the Fixture: `provider_factory`

Your fixture must provide a configurable Circuit Breaker instance.
```info
The factory must return an **async function** that accepts configuration parameters:
- `failure_threshold (int)`: The number of failures required to trip the circuit to the OPEN state.
- `reset_timeout (float)`: The number of seconds to wait in the OPEN state before transitioning to HALF_OPEN.
The provider instance itself must expose an `execute(callable)` method and a `state` property.
```

### Example Fixture Implementation

```python
# tests/compliance/test_my_breaker_compliance.py
import pytest
from tck_py.resilience.circuit_breaker import BaseTestCircuitBreakerContract
from my_project.resilience.my_breaker import MyCircuitBreaker

class TestMyBreakerCompliance(BaseTestCircuitBreakerContract):

    @pytest.fixture
    def provider_factory(self):
        """
        Provides the TCK with configured instances of our Circuit Breaker.
        """
        async def _factory(failure_threshold: int, reset_timeout: float):
            return MyCircuitBreaker(
                failure_threshold=failure_threshold,
                reset_timeout=reset_timeout
            )

        return _factory
```

## Contract Test Breakdown

---

### `test_initial_state_is_closed`

-   **Purpose**: Verifies that a new breaker starts in a healthy, operational state.
-   **Behavior**: Asserts that a newly created breaker instance has its `state` property equal to `CircuitState.CLOSED`.
---

### `test_transitions_to_open_after_failures`

-   **Purpose**: Validates o core "tripping" mechanism.
-   **Behavior**: The test configures a breaker with a low `failure_threshold` (e.g., 2).
It then executes a failing operation twice.
-   **Requirement**: After the second failure, the breaker's state **must** transition to `CircuitState.OPEN`.
A subsequent call **must** fail immediately with a ```tck_py.shared.exceptions.CircuitOpenError``` without executing the underlying operation.
---

### `test_transitions_to_half_open_after_timeout`

-   **Purpose**: Verifies the recovery mechanism after a failure period.
-   **Behavior**: The test trips the breaker to `OPEN`, waits for a duration longer than the `reset_timeout`, and then asserts that the breaker's state has transitioned to `CircuitState.HALF_OPEN`.
---

### `test_half_open_to_closed_on_success`

-   **Purpose**: Validates the "self-healing" path where a trial call succeeds.
-   **Behavior**: After putting the breaker into the `HALF_OPEN` state, the test executes a *successful* operation.
-   **Requirement**: Upon success, the breaker's state **must** immediately transition back to `CircuitState.CLOSED`.
---

### `test_half_open_to_open_on_failure`

-   **Purpose**: Validates the path where a trial call in the half-open state fails.
-   **Behavior**: After putting the breaker into the `HALF_OPEN` state, the test executes a *failing* operation.
-   **Requirement**: Upon failure, the breaker's state **must** immediately transition back to `CircuitState.OPEN`, restarting the reset timeout.
