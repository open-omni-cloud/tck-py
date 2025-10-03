# src/tck_py/observability/tracing.py
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.trace import StatusCode

TRACER_NAME = "tck.tracer"


@pytest.mark.asyncio
class BaseTestTracingContract:
    """
    TCK Contract: Defines the compliance test suite for tracing instrumentation.

    This contract verifies that any provider operation is correctly instrumented
    with OpenTelemetry, creating child spans with appropriate attributes and
    status.
    """

    @pytest.fixture
    # The fixture signature is simplified here as it's defined in the concrete class
    def instrumented_provider_factory(
        self,
    ) -> Callable[..., Awaitable[tuple[Any, Callable[[], list[Any]]]]]:
        """
        This fixture MUST be implemented by the inheriting test class.

        It needs to return an async factory function that, when awaited,
        must return a tuple of two items:

        1. A provider instance to be tested.
        2. A `get_finished_spans` function that returns a list of all spans
           captured by an in-memory exporter since it was last called.

        The implementation of this fixture is responsible for setting up the
        OpenTelemetry SDK with an InMemorySpanExporter and associating it with
        the created provider.
        """
        raise NotImplementedError(
            "To use the TCK, you must implement the "
            "'instrumented_provider_factory' fixture."
        )

    @pytest.fixture
    def expected_attributes(self) -> dict:
        """
        This fixture should be overridden by the inheriting test class to
        provide a dictionary of attributes expected on the span.
        e.g., {"db.system": "redis", "db.operation": "SET"}
        """
        return {}

    # --- Start of Contract Tests ---

    async def test_operation_creates_child_span(self, instrumented_provider_factory):
        """
        Verifies that a provider operation creates a new span that is a child
        of the active OpenTelemetry context.
        """
        tracer = trace.get_tracer(TRACER_NAME)

        # The fixture provides the tuple directly, no await needed here
        provider, get_finished_spans = instrumented_provider_factory

        with tracer.start_as_current_span("test-parent-span") as parent_span:
            # Perform a generic operation on the provider
            await provider.some_operation()

            parent_context = parent_span.get_span_context()
            finished_spans = get_finished_spans()

            assert (
                len(finished_spans) >= 1
            ), "At least one span should have been created."

            child_span = finished_spans[0]
            assert child_span.parent is not None
            assert child_span.parent.span_id == parent_context.span_id
            assert child_span.name is not None and len(child_span.name) > 0

    async def test_span_has_expected_attributes(
        self, instrumented_provider_factory, expected_attributes
    ):
        """
        Verifies that the span created by the provider operation contains
        the expected semantic attributes.
        """
        tracer = trace.get_tracer(TRACER_NAME)

        # The fixture provides the tuple directly, no await needed here
        provider, get_finished_spans = instrumented_provider_factory

        with tracer.start_as_current_span("test-parent-span"):
            await provider.some_operation()

            finished_spans = get_finished_spans()
            assert len(finished_spans) >= 1

            child_span = finished_spans[0]
            for key, value in expected_attributes.items():
                assert key in child_span.attributes
                assert child_span.attributes[key] == value

    async def test_failed_operation_sets_span_status_to_error(
        self, instrumented_provider_factory
    ):
        """
        Verifies that if a provider operation fails with an exception, the
        span's status is correctly set to Error.
        """
        tracer = trace.get_tracer(TRACER_NAME)

        provider, get_finished_spans = instrumented_provider_factory

        with tracer.start_as_current_span("test-parent-span"):
            # The fixture is expected to be parametrized
            # by the inheriting class to inject 'should_fail=True'

            with pytest.raises(ValueError):
                await provider.some_operation()

            finished_spans = get_finished_spans()
            assert len(finished_spans) >= 1

            child_span = finished_spans[0]
            assert child_span.status.status_code == StatusCode.ERROR
            assert (
                child_span.status.description is not None
                and len(child_span.status.description) > 0
            )
