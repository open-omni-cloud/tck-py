# tests/reference/observability/test_in_memory_metrics.py
import asyncio
import logging
import time
import uuid

import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

# TCK Contract Imports
from tck_py.observability.metrics import BaseTestMetricsContract

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

    async def some_operation(self):
        """A generic method instrumented with tracing and metrics."""

        # Instrumentation setup for tracing (Tracer will be None in Metrics tests)
        tracer_span = None
        span = None
        if self._tracer:
            tracer_span = self._tracer.start_as_current_span(
                "InMemoryObservableProvider.some_operation"
            )
            span = tracer_span.__enter__()

        start_time = time.monotonic()
        attributes = {"operation": "execute"}

        try:
            if self._should_fail:
                raise ValueError("Operation failed as configured.")

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

            if self._tracer and tracer_span:
                tracer_span.__exit__(None, None, None)

    async def some_operation_that_logs(self, message: str):
        pass


# =============================================================================
# 2. TCK COMPLIANCE TESTS (METRICS)
# =============================================================================


class TestInMemoryMetricsCompliance(BaseTestMetricsContract):
    @staticmethod
    def _extract_metrics_data(reader):
        # Get metrics data
        data = reader.get_metrics_data()
        metrics_dict = {}
        if data and data.resource_metrics:
            for rm in data.resource_metrics:
                for sm in rm.scope_metrics:
                    for metric in sm.metrics:
                        metrics_dict[metric.name] = metric.data.data_points
        return metrics_dict

    @pytest.fixture
    def instrumented_provider_factory(self, request):
        should_fail = False
        if hasattr(request, "param"):
            param = request.param
            if isinstance(param, dict):
                should_fail = param.get("should_fail", False)

        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[reader])

        try:
            meter = meter_provider.get_meter("in-memory.provider")
            provider = InMemoryObservableProvider(
                tracer=None, meter=meter, should_fail=should_fail
            )

            yield provider, lambda: self._extract_metrics_data(reader)

        finally:
            # Shutdown to ensure all metrics are processed
            meter_provider.shutdown()

    @pytest.fixture
    def expected_operation_name(self) -> str:
        return "execute"

    @pytest.fixture
    def expected_metric_names(self) -> dict:
        return {
            "duration": "my.provider.operation.duration",
            "calls": "my.provider.operation.calls.total",
        }

    # Parametrization for error testing (Corrected Missing Arguments)
    @pytest.mark.parametrize(
        "instrumented_provider_factory", [{"should_fail": True}], indirect=True
    )
    async def test_failed_operation_increments_counter_with_error_status(
        self,
        instrumented_provider_factory,
        expected_metric_names,
        expected_operation_name,
    ):
        await super().test_failed_operation_increments_counter_with_error_status(
            instrumented_provider_factory,
            expected_metric_names,
            expected_operation_name,
        )
