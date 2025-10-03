# src/tck_py/shared/models.py
"""
This module defines the canonical data models that the TCK contracts
use and expect.

These models create an explicit data contract for provider implementations
and test fixtures.
"""

from enum import Enum, auto
from typing import Any, NamedTuple

# --- Messaging ---


class ConsumedMessage(NamedTuple):
    """Represents the structure of a message delivered to a consumer handler."""

    payload: bytes
    key: str | None
    headers: dict[str, Any]


# --- Resilience ---


class OutboxEvent(NamedTuple):
    """
    Represents the data structure for an outbox event to be saved.
    This model is used as input for the OutboxStorage repository.
    """

    destination_topic: str
    payload: bytes
    message_key: str | None = None
    aggregate_key: str | None = None


class SagaStepHistory(NamedTuple):
    """Represents a single step's history in a saga's state."""

    step_name: str
    status: str


class SagaState(NamedTuple):
    """Represents the state of a running saga instance."""

    saga_id: str
    status: str
    current_step: int
    history: list[SagaStepHistory]
    payload: dict[str, Any]
    version: int


class CircuitState(Enum):
    """Represents the possible states of a Circuit Breaker."""

    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()
