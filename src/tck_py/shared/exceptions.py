# src/tck_py/shared/exceptions.py
"""
This module defines a set of standardized, vendor-agnostic exceptions
that TCK-compliant providers are expected to raise under specific
failure conditions.

This ensures that consumers of the abstraction layer can write portable
error-handling logic.
"""


class TCKError(Exception):
    """Base exception for all Open Omni-Cloud TCK-related errors."""

    pass


# --- Security ---
class SecretNotFoundError(TCKError):
    """Raised when a secret is not found in the backend."""

    pass


# --- Primitives ---
class ObjectNotFoundError(TCKError):
    """Raised when an object is not found in the storage backend."""

    pass


# --- Messaging ---
class PublishError(TCKError):
    """
    Raised when a message fails to be published to the broker, for example,
    due to a connection failure.
    """

    pass


# --- Resilience ---
class SagaStateConflictError(TCKError):
    """
    Raised when a saga state update fails due to a version mismatch
    (optimistic concurrency control).
    """

    pass


class CircuitOpenError(TCKError):
    """
    Raised when an operation is blocked because the circuit breaker is in
    the OPEN state.
    """

    pass
