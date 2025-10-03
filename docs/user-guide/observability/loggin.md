# User Guide: Implementing the Structured Logging Contract

Structured, context-aware logging is a core tenet of modern observability. Instead of plain text, logs should be emitted as machine-readable JSON, automatically enriched with execution context like trace and tenant IDs.

This guide details how to ensure your provider is compliant with the structured logging requirements of the Open Omni-Cloud standard by satisfying the `TestStructuredLoggingContract`.

## Contract Overview

**TCK Class:** ```tck_py.observability.logging.TestStructuredLoggingContract```

The `TestStructuredLoggingContract` validates two key aspects of your provider's logging:
1.  **Format**: Logs are emitted as valid JSON strings.
2.  **Context Injection**: Active `trace_id` and `tenant_id` values are automatically included in the log structure.

## Implementing the Fixture: `instrumented_provider_factory`

This fixture is responsible for capturing log output during a test.

```info
The factory must return an **async function** that accepts optional `trace_context` and `tenant_id`. When awaited, it must provide a tuple containing:
1.  An **instrumented provider instance** to be tested.
2.  An `io.StringIO` **stream object** that captures all log output from the provider's logger.
```

Your fixture implementation needs to temporarily reconfigure the Python `logging` module to redirect a logger's output to this in-memory stream.

### Example Fixture Implementation

```python
# tests/compliance/test_my_provider_logging_compliance.py
import pytest
import logging
import io
import json
from tck_py.observability.logging import TestStructuredLoggingContract
# ... other imports

class TestMyProviderLoggingCompliance(TestStructuredLoggingContract):

    @pytest.fixture
    def instrumented_provider_factory(self):
        """
        Sets up a logging pipeline to capture structured logs in memory.
        """
        async def _factory(trace_context=None, tenant_id=None):
            # Setup context (e.g., using contextvars) so the logger can find it
            setup_execution_context(trace_context, tenant_id)

            log_stream = io.StringIO()

            # Get the logger your provider uses
            provider_logger = logging.getLogger("my_project.providers.my_provider")

            # Temporarily add a handler to capture logs to the stream
            handler = logging.StreamHandler(log_stream)
            provider_logger.addHandler(handler)

            provider = MyProvider() # Assume provider uses the logger internally

            # A real implementation would need to handle teardown
            # (e.g., removing the handler) via a yield or a finalizer.

            return provider, log_stream

        return _factory
```

## Contract Test Breakdown

---

### `test_log_is_valid_json`

-   **Purpose**: Verifies the fundamental requirement of structured logging.
-   **Behavior**: The test executes a provider operation that logs a message, captures the output, and asserts that it can be successfully parsed as JSON.

---

### `test_log_contains_standard_fields`

-   **Purpose**: Ensures logs contain a baseline of useful information.
-   **Behavior**: After parsing the JSON log, this test asserts the presence of standard keys like `timestamp`, `level`, and `message`.

---

### `test_log_injects_trace_context`

-   **Purpose**: A critical test for observability. It verifies that logs can be correlated with traces.
-   **Behavior**: The TCK activates a parent trace span, then calls your provider's operation.
-   **Requirement**: The resulting JSON log **must** contain a `trace_id` field whose value matches the active span's trace ID.

---

### `test_log_injects_tenant_context`

-   **Purpose**: Validates a key requirement for multi-tenant systems and portable policies.
-   **Behavior**: The TCK establishes a tenant context before calling your provider's operation.
-   **Requirement**: The resulting JSON log **must** contain a `tenant_id` field that matches the active tenant ID.
