# src/tck_py/observability/metrics.py
from collections.abc import Awaitable, Callable
from typing import Any

import pytest


@pytest.mark.asyncio
class BaseTestMetricsContract:
    """
    TCK Contract: Defines the compliance test suite for metrics instrumentation.

    This contract verifies that any provider operation is correctly instrumented
    with OpenTelemetry to emit standard metrics like counters and histograms.
    """

    @pytest.fixture
    def instrumented_provider_factory(
        self,
    ) -> Callable[..., Awaitable[tuple[Any, Callable[[], dict]]]]:
        """
        This fixture MUST be implemented by the inheriting test class.

        It needs to return an async factory function. This factory, when awaited,
        must return a tuple of two items:

        1. A provider instance to be tested.
        2. A `get_metrics_data` function that returns a dictionary of all metric
           data captured by an in-memory reader.

        The implementation is responsible for setting up the OpenTelemetry
        MeterProvider with an InMemoryMetricReader.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the "
            "'instrumented_provider_factory' fixture."
        )

    @pytest.fixture
    def expected_operation_name(self) -> str:
        """
        The name of the operation being tested, to be used in attributes.
        e.g., "SET", "GET", "PUBLISH"
        """
        return "some.operation"

    @pytest.fixture
    def expected_metric_names(self) -> dict[str, str]:
        """
        A dictionary mapping metric types to their expected names.
        e.g., {
            "duration": "db.client.operations.duration",
            "calls": "db.client.operations.total"
        }
        """
        return {}

    # --- Start of Contract Tests ---

    async def test_successful_operation_increments_counter(
        self,
        instrumented_provider_factory,
        expected_metric_names,
        expected_operation_name,
    ):
        """
        Verifies that a successful provider operation increments a standard counter
        with a 'status' attribute of 'success'.
        """
        if "calls" not in expected_metric_names:
            pytest.skip("Calls counter metric name not defined for this provider.")

        # FIX: Remove 'await'. Fixture returns the tuple directly.
        provider, get_metrics_data = instrumented_provider_factory

        await provider.some_operation()

        metrics = get_metrics_data()
        counter_name = expected_metric_names["calls"]

        assert counter_name in metrics, f"Metric '{counter_name}' not found."

        data_points = metrics[counter_name]
        assert len(data_points) >= 1

        # Find the specific data point for our successful operation
        success_point = next(
            (
                p
                for p in data_points
                if p.attributes.get("status") == "success"
                and p.attributes.get("operation") == expected_operation_name
            ),
            None,
        )

        assert (
            success_point is not None
        ), "No counter data point found with status='success'."
        assert success_point.value == 1

    async def test_failed_operation_increments_counter_with_error_status(
        self,
        instrumented_provider_factory,
        expected_metric_names,
        expected_operation_name,
    ):
        """
        Verifies that a failed provider operation increments a standard counter
        with a 'status' attribute of 'error'.
        """
        if "calls" not in expected_metric_names:
            pytest.skip("Calls counter metric name not defined for this provider.")

        # FIX: Remove 'await'. Fixture returns the tuple directly.
        provider, get_metrics_data = instrumented_provider_factory

        # Capture the specific ValueError raised by the reference implementation
        with pytest.raises(ValueError):
            await provider.some_operation()

        metrics = get_metrics_data()
        counter_name = expected_metric_names["calls"]
        assert counter_name in metrics

        data_points = metrics[counter_name]
        error_point = next(
            (
                p
                for p in data_points
                if p.attributes.get("status") == "error"
                and p.attributes.get("operation") == expected_operation_name
            ),
            None,
        )

        assert (
            error_point is not None
        ), "No counter data point found with status='error'."
        assert error_point.value == 1

    async def test_operation_records_duration_in_histogram(
        self,
        instrumented_provider_factory,
        expected_metric_names,
        expected_operation_name,
    ):
        """
        Verifies that a provider operation's duration is recorded in a histogram.
        """
        if "duration" not in expected_metric_names:
            pytest.skip("Duration histogram metric name not defined for this provider.")

        # FIX: Remove 'await'. Fixture returns the tuple directly.
        provider, get_metrics_data = instrumented_provider_factory

        # The duration is measured inside the operation itself.
        await provider.some_operation()

        metrics = get_metrics_data()
        histogram_name = expected_metric_names["duration"]
        assert histogram_name in metrics

        data_points = metrics[histogram_name]

        histogram_point = next(
            (
                p
                for p in data_points
                if p.attributes.get("operation") == expected_operation_name
            ),
            None,
        )

        assert (
            histogram_point is not None
        ), "No histogram data point found for the operation."
        assert histogram_point.count == 1
        assert histogram_point.sum > 0
