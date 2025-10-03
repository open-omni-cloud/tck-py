# User Guide: Implementing the Tracing Contract

Distributed tracing is a cornerstone of observability in microservices. It allows you to visualize the entire lifecycle of a request as it travels through multiple services, making it an indispensable tool for debugging and performance analysis.

The Open Omni-Cloud standard requires all providers to be correctly instrumented with OpenTelemetry. This TCK contract validates that instrumentation.

## Contract Overview

**TCK Class:** ```tck_py.observability.tracing.TestTracingContract```

The `TestTracingContract` does not test the provider's business logic. Instead, it tests the **telemetry it emits**. It verifies that for any given operation, the provider:
1.  Creates a new OpenTelemetry span.
2.  Correctly parents this new span to any active span context.
3.  Enriches the span with meaningful, standardized attributes.
4.  Sets the span's status correctly in case of an error.

## Implementing the Fixture: `instrumented_provider_factory`

To test tracing, the TCK needs a way to capture the spans your provider emits. This is handled by a specialized fixture.

```info
The factory must return an **async function** that, when awaited, provides a tuple containing:
1.  An **instrumented provider instance** to be tested.
2.  A `get_finished_spans` helper function that returns all spans captured by an in-memory exporter.
```

Your fixture implementation is responsible for the temporary setup of the OpenTelemetry SDK with an `InMemorySpanExporter`.

### Example Fixture Implementation

This is a more advanced fixture. Here is a blueprint for how to implement it.

```python
# tests/compliance/test_my_provider_tracing_compliance.py
import pytest
from tck_py.observability.tracing import TestTracingContract
from my_project.providers.my_provider import MyProvider

# OTel SDK imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, InMemorySpanExporter

class TestMyProviderTracingCompliance(TestTracingContract):

    @pytest.fixture
    def instrumented_provider_factory(self):
        """
        This factory sets up an OTel pipeline to capture spans in memory
        and provides an instrumented provider.
        """
        async def _factory(should_fail=False):
            # 1. Setup the in-memory exporter
            tracer_provider = TracerProvider()
            memory_exporter = InMemorySpanExporter()
            processor = SimpleSpanProcessor(memory_exporter)
            tracer_provider.add_span_processor(processor)

            # A real implementation would associate this provider with the
            # provider instance (e.g., via dependency injection).

            # 2. Create the provider instance
            provider = MyProvider(tracer_provider=tracer_provider, should_fail=should_fail)

            # 3. Define the helper to get finished spans
            def get_finished_spans():
                # The processor must be forced to flush to ensure spans are exported
                processor.force_flush()
                return memory_exporter.get_finished_spans()

            return provider, get_finished_spans

        return _factory

    @pytest.fixture
    def expected_attributes(self) -> dict:
        """
        Overrides the fixture to define the attributes this specific
        provider's 'some_operation' is expected to add to its span.
        """
        return {"my.provider.system": "awesome_system", "my.provider.operation": "execute"}
```

## Contract Test Breakdown

The following tests are defined in `TestTracingContract` and will be run against your provider.

---

### `test_operation_creates_child_span`

-   **Purpose**: This is the core test for distributed context propagation. It verifies that your provider correctly continues a trace started by a calling service.
-   **Behavior**: The TCK creates a "parent span." It then calls a method on your provider (e.g., `await provider.some_operation()`).
-   **Requirement**: Your provider's operation **must** create its own "child span." The test asserts that the new span's parent ID matches the parent span's ID.

---

### `test_span_has_expected_attributes`

-   **Purpose**: Ensures that spans are enriched with meaningful, queryable metadata.
-   **Behavior**: The test calls a provider operation and inspects the attributes (tags) of the span it creates.
-   **Requirement**: The span's attributes must contain the key-value pairs that you define in the `expected_attributes` fixture in your test class.

---

### `test_failed_operation_sets_span_status_to_error`

-   **Purpose**: Validates that your instrumentation correctly records failures.
-   **Behavior**: The TCK calls your `instrumented_provider_factory` with `should_fail=True`. It then executes the provider operation, which is expected to raise an exception.
-   **Requirement**: The span created for the failed operation **must** have its status set to `StatusCode.ERROR` and should include a description of the error. This is critical for calculating error rates and debugging production issues.
