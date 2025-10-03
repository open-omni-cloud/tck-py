# tests/reference/observability/test_in_memory_logging.py
import asyncio
import io
import json
import logging
import uuid

import pytest
from opentelemetry import metrics, trace

# TCK Contract Imports
from tck_py.observability.logging import BaseTestStructuredLoggingContract

# =============================================================================
# 1. PROVIDER IMPLEMENTATION (Shared)
# =============================================================================


class InMemoryObservableProvider:
    """
    A simple provider instrumented for tracing/metrics, used as a reference.
    """

    def __init__(
        self,
        tracer: trace.Tracer | None,
        meter: metrics.Meter | None,
        should_fail: bool = False,
    ):
        self._tracer = tracer
        self._meter = meter
        self._should_fail = should_fail
        self._logger = logging.getLogger(f"test-logger-{uuid.uuid4()}")

    async def some_operation(self):
        if self._should_fail:
            raise ValueError("Operation failed as configured.")
        await asyncio.sleep(0.01)

    async def some_operation_that_logs(self, message: str):
        """A generic method instrumented for logging tests."""
        await asyncio.sleep(0)
        self._logger.info(message)


# =============================================================================
# 2. TCK COMPLIANCE TESTS (LOGGING)
# =============================================================================


class TestInMemoryLoggingCompliance(BaseTestStructuredLoggingContract):
    @pytest.fixture
    async def instrumented_provider_factory(self, request):
        param = getattr(request, "param", {})

        trace_context = param.get("trace_context")
        tenant_id = param.get("tenant_id")

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)

        class ContextFormatter(logging.Formatter):
            def format(self, record):
                log_json = {
                    "message": record.getMessage(),
                    "level": record.levelname,
                }
                if trace_context:
                    log_json["trace_id"] = f"{trace_context.trace_id:032x}"
                if tenant_id:
                    log_json["tenant_id"] = tenant_id

                log_json["timestamp"] = self.formatTime(record, self.datefmt)

                return json.dumps(log_json)

        handler.setFormatter(ContextFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
        logger_name = f"tck-logger-{uuid.uuid4()}"
        logger = logging.getLogger(logger_name)

        if logger.hasHandlers():
            logger.handlers.clear()

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        provider_instance = InMemoryObservableProvider(tracer=None, meter=None)
        provider_instance._logger = logger

        try:
            if tenant_id:
                yield provider_instance, log_stream, tenant_id
            else:
                yield provider_instance, log_stream

        finally:
            logger.removeHandler(handler)

    # Parametrization for trace context injection
    @pytest.mark.parametrize(
        "instrumented_provider_factory",
        [
            {
                "trace_context": trace.get_tracer("tck.tracer")
                .start_span("test-setup-span")
                .get_span_context()
            }
        ],
        indirect=True,
    )
    async def test_log_injects_trace_context(self, instrumented_provider_factory):
        await super().test_log_injects_trace_context(instrumented_provider_factory)

    # Parametrization for tenant context injection
    @pytest.mark.parametrize(
        "instrumented_provider_factory",
        [{"tenant_id": f"tenant-{uuid.uuid4()}"}],
        indirect=True,
    )
    async def test_log_injects_tenant_context(self, instrumented_provider_factory):
        """
        Overrides the base test to assert the specific parametrized tenant_id value.
        """
        provider, log_stream, expected_tenant_id = instrumented_provider_factory

        # Execute the logging operation
        await provider.some_operation_that_logs("message with tenant")

        # NOTE: We call the base test here to ensure the "tenant_id" field exists
        # Then, we perform the value assertion using the specific UUID
        log_data = json.loads(log_stream.getvalue())

        assert "tenant_id" in log_data
        assert log_data["tenant_id"] == expected_tenant_id
