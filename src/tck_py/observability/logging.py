# src/tck_py/observability/logging.py
import io
import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from opentelemetry import trace


@pytest.mark.asyncio
class BaseTestStructuredLoggingContract:
    """
    TCK Contract: Defines the compliance test suite for structured logging.
    This contract verifies that providers emit logs in a structured (JSON)
    format and that execution context (e.g., trace_id, tenant_id) is
    automatically injected into the log records.
    """

    @pytest.fixture
    def instrumented_provider_factory(
        self,
    ) -> Callable[..., Awaitable[tuple[Any, io.StringIO]]]:
        """
        This fixture MUST be implemented by the inheriting test class.
        It needs to return an async factory function that accepts optional context:
        - `trace_context`: An active OpenTelemetry SpanContext.
        - `tenant_id`: A string representing the tenant.

        The factory, when awaited, must return a tuple of two items:

        1. A provider instance to be tested.
        2. An `io.StringIO` stream object that captures the log output from
           the provider's logger. The implementation is responsible for
           configuring a logger with a StreamHandler pointing to this
           StringIO object for the test's duration.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the "
            "'instrumented_provider_factory' fixture."
        )

    async def test_log_is_valid_json(self, instrumented_provider_factory):
        """Verifies that the log output is a valid JSON string."""
        provider, log_stream = instrumented_provider_factory

        await provider.some_operation_that_logs("test message")

        log_output = log_stream.getvalue().strip()
        assert log_output, "Log output should not be empty."

        try:
            log_data = json.loads(log_output)
            assert isinstance(log_data, dict)
            assert "timestamp" in log_data
        except json.JSONDecodeError:
            pytest.fail(f"Log output is not valid JSON: {log_output}")

    async def test_log_contains_standard_fields(self, instrumented_provider_factory):
        """Verifies that the structured log contains essential fields."""
        provider, log_stream = instrumented_provider_factory
        test_message = f"log-event-{uuid.uuid4()}"

        await provider.some_operation_that_logs(test_message)

        log_data = json.loads(log_stream.getvalue())

        assert "timestamp" in log_data
        assert "level" in log_data
        assert "message" in log_data
        assert log_data["message"] == test_message

    async def test_log_injects_trace_context(self, instrumented_provider_factory):
        """Verifies that an active trace_id is automatically injected into the log."""
        tracer = trace.get_tracer("tck.tracer")

        # The test context must be set up before calling the logging operation
        with tracer.start_as_current_span("parent-span-for-logging") as parent_span:
            span_context = parent_span.get_span_context()

            provider, log_stream = instrumented_provider_factory

            await provider.some_operation_that_logs("message with trace")

            log_data = json.loads(log_stream.getvalue())

            assert "trace_id" in log_data
            assert log_data["trace_id"] == f"{span_context.trace_id:032x}"

    async def test_log_injects_tenant_context(self, instrumented_provider_factory):
        """
        Verifies that an active tenant_id is automatically injected into the log.
        This base method only verifies the existence of the field.
        The concrete test must assert the specific parameterized value.
        """
        provider, log_stream = instrumented_provider_factory

        await provider.some_operation_that_logs("message with tenant")

        log_data = json.loads(log_stream.getvalue())

        assert "tenant_id" in log_data
