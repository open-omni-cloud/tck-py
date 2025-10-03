# ADR-004: Centralized `shared` Module for Core Entities

* **Status:** Accepted
* **Date:** 2025-10-03

## Context

During initial development, common entities like custom exceptions (`SecretNotFoundError`) and data models (`SagaState`) were defined locally within each contract file. This led to code duplication, violated the DRY (Don't Repeat Yourself) principle, and created an implicit, scattered contract for the TCK's core entities.

## Decision

We will create a centralized `tck_py/shared/` module to house all common, shared code. This includes:
-   `shared/exceptions.py`: For all standardized TCK exceptions.
-   `shared/models.py`: For all canonical data models used in the test contracts.

All contract files will import these entities from the `shared` module instead of defining them locally.

## Consequences

* **Positive:**
    * Creates a single source of truth for the TCK's error and data contracts.
    * Eliminates code duplication, improving long-term maintainability.
    * Makes the TCK's core contracts (the expected data structures and errors) explicit and easy for a developer to find.
* **Negative:**
    * Adds a small degree of indirection (imports from a shared module), but this is a standard and acceptable trade-off.
