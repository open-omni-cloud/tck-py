# User Guide: Implementing the Metrics Contract

Metrics are a fundamental pillar of observability, providing the quantitative data needed to monitor system health, trigger alerts, and understand performance characteristics. Key metrics like operation counts and duration are the foundation for calculating the "Golden Signals" (Latency, Traffic, Errors).

The Open Omni-Cloud standard requires all providers to be instrumented with OpenTelemetry to emit a standard set of metrics. This TCK contract validates that instrumentation.

## Contract Overview

**TCK Class:** ```tck_py.observability.metrics.TestMetricsContract```

The `TestMetricsContract` verifies that a provider's operations emit the expected metrics. It checks for:
1.  A **counter** that increments for each operation, tagged by status (`success`/`error`).
2.  A **histogram** that records the duration of each operation.

## Implementing the Fixture: `instrumented_provider_factory`

Similar to the tracing contract, testing metrics requires a specialized fixture to capture the telemetry your provider emits.

```info
The factory must return an **async function** that, when awaited, provides a tuple containing:
1.  An **instrumented provider instance** to be tested.
2.  A `get_metrics_data` helper function that returns all metrics captured by an in-memory reader.
```

Your fixture implementation is responsible for the temporary setup of the OpenTelemetry SDK with an `InMemoryMetricReader`.

### Example Fixture Implementation

The setup is very similar to the tracing fixture, but using the OTel Metrics SDK components.

```python
# tests/compliance/test_my_provider_metrics_compliance.py
import pytest
from tck_py.observability.metrics import TestMetricsContract
from my_project.providers.my_provider import MyProvider

# OTel SDK imports
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

class TestMyProviderMetricsCompliance(TestMetricsContract):

    @pytest.fixture
    def instrumented_provider_factory(self):
        """
        Sets up an OTel pipeline to capture metrics in memory.
        """
        async def _factory(should_fail=False):
            # 1. Setup the in-memory reader
            reader = InMemoryMetricReader()
            provider = MeterProvider(metric_readers=[reader])

            # 2. Create the provider instance, injecting the MeterProvider
            meter = provider.get_meter("my.provider.meter")
            provider_instance = MyProvider(meter=meter, should_fail=should_fail)

            # 3. Define the helper to get metric data
            def get_metrics_data():
                # The data structure is complex, this is a simplified representation
                return reader.get_metrics_data()

            return provider_instance, get_metrics_data

        return _factory

    @pytest.fixture
    def expected_operation_name(self) -> str:
        return "execute"

    @pytest.fixture
    def expected_metric_names(self) -> dict:
        return {
            "duration": "my.provider.operation.duration",
            "calls": "my.provider.operation.calls.total"
        }
```

## Contract Test Breakdown

The following tests are defined in `TestMetricsContract` and will be run against your provider.

---

### `test_successful_operation_increments_counter`

-   **Purpose**: Verifies that successful operations are counted, providing the basis for the "Traffic" golden signal.
-   **Behavior**: The test calls a successful provider operation. It then inspects the captured metrics to find the counter specified by `expected_metric_names["calls"]`.
-   **Requirement**: The test asserts that a data point for this counter exists with a value of `1` and an attribute `status="success"`.

---

### `test_failed_operation_increments_counter_with_error_status`

-   **Purpose**: Verifies that failed operations are counted separately, providing the basis for the "Errors" golden signal.
-   **Behavior**: The test calls a provider operation that is configured to fail.
-   **Requirement**: It asserts that a data point for the `calls` counter exists with a value of `1` and an attribute `status="error"`. This distinction between success and error statuses is critical for calculating error rates.

---

### `test_operation_records_duration_in_histogram`

-   **Purpose**: Verifies that operation latency is measured, providing the basis for the "Latency" golden signal.
-   **Behavior**: The test calls a provider operation and inspects the captured metrics for the histogram specified by `expected_metric_names["duration"]`.
-   **Requirement**: The test asserts that the histogram has recorded exactly one measurement (`count=1`) and that its value (`sum`) is a positive number, confirming that the operation's duration was recorded.
