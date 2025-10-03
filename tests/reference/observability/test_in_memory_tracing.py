# tests/reference/observability/test_in_memory_tracing.py
import asyncio
import logging
import time
import uuid

import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# TCK Contract Imports
from tck_py.observability.tracing import BaseTestTracingContract

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

        if self._meter:
            self._calls_counter = self._meter.create_counter(
                "my.provider.operation.calls.total",
                description="Counts the number of operations.",
            )
            self._duration_histogram = self._meter.create_histogram(
                "my.provider.operation.duration",
                description="Measures the duration of operations.",
                unit="s",
            )

        self._logger = logging.getLogger(f"test-logger-{uuid.uuid4()}")

    async def some_operation(self):
        """A generic method instrumented with tracing and metrics."""

        tracer_span = None
        span = None
        if self._tracer:
            tracer_span = self._tracer.start_as_current_span(
                "InMemoryObservableProvider.some_operation"
            )
            span = tracer_span.__enter__()
            span.set_attribute("my.provider.system", "in-memory")
            span.set_attribute("my.provider.operation", "execute")

        start_time = time.monotonic()
        attributes = {"operation": "execute"}

        try:
            if self._should_fail:
                raise ValueError("Operation failed as configured.")

            # Simulated business operation
            await asyncio.sleep(0.01)

            # Record success metrics/status
            if self._meter:
                self._calls_counter.add(1, {**attributes, "status": "success"})
            if self._tracer:
                span.set_status(trace.Status(trace.StatusCode.OK))

        except Exception as e:
            if self._meter:
                self._calls_counter.add(1, {**attributes, "status": "error"})
            if self._tracer and span:
                span.set_status(
                    trace.Status(trace.StatusCode.ERROR, description=str(e))
                )
            raise

        finally:
            # Record duration regardless of success/failure
            duration = time.monotonic() - start_time
            if self._meter:
                self._duration_histogram.record(duration, attributes)

            # Close the span if it was opened
            if self._tracer and tracer_span:
                tracer_span.__exit__(None, None, None)

    async def some_operation_that_logs(self, message: str):
        """A generic method that logs messages."""
        pass


# =============================================================================
# 2. TCK COMPLIANCE TESTS (TRACING)
# =============================================================================


class TestInMemoryTracingCompliance(BaseTestTracingContract):
    @pytest.fixture
    async def instrumented_provider_factory(self, request):
        should_fail = (
            request.param.get("should_fail", False)
            if hasattr(request, "param") and isinstance(request.param, dict)
            else False
        )

        tracer_provider = TracerProvider()
        memory_exporter = InMemorySpanExporter()
        processor = SimpleSpanProcessor(memory_exporter)
        tracer_provider.add_span_processor(processor)

        original_provider = trace.get_tracer_provider()
        trace.set_tracer_provider(tracer_provider)

        try:
            tracer = tracer_provider.get_tracer("in-memory.provider")
            provider = InMemoryObservableProvider(
                tracer=tracer, meter=None, should_fail=should_fail
            )

            def get_finished_spans():
                processor.force_flush()
                spans = memory_exporter.get_finished_spans()
                memory_exporter.clear()
                return spans

            yield provider, get_finished_spans

        finally:
            trace.set_tracer_provider(original_provider)

    @pytest.fixture
    def expected_attributes(self) -> dict:
        return {"my.provider.system": "in-memory", "my.provider.operation": "execute"}

    # Parametrization for error testing
    @pytest.mark.parametrize(
        "instrumented_provider_factory", [{"should_fail": True}], indirect=True
    )
    async def test_failed_operation_sets_span_status_to_error(
        self, instrumented_provider_factory
    ):
        await super().test_failed_operation_sets_span_status_to_error(
            instrumented_provider_factory
        )
