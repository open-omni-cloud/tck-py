# ADR-002: Pytest-based Contract Inheritance with Fixture Injection

* **Status:** Accepted
* **Date:** 2025-10-03

## Context

The TCK needs a mechanism that allows provider developers to run the compliance suite against their code with minimal boilerplate.
The mechanism should be familiar to the Python community and powerful enough to handle complex setup and teardown logic for integration tests.
We considered a function-based approach or a custom test runner, but these would be less familiar and more complex to implement.
## Decision

We will build the TCK on top of `pytest`.
Each contract will be an abstract-like base class (e.g., `TestKVStoreContract`) containing all the test methods.
A provider developer will create their own test class that **inherits** from the TCK's contract class.
The connection between the abstract tests and the concrete implementation will be made via a mandatory `pytest` **fixture** (e.g., `provider_factory`) that the developer must implement to inject their provider instance.

This inheritance model also supports **compositional testing** by allowing test classes to inherit from multiple TCK contract classes, notably the [Policy Mixin Contracts](./ADR-003-mixin-classes-for-policy-contracts.md). In such cases, the developer's single `provider_factory` must satisfy the combined requirements of all inherited contracts.

## Consequences

* **Positive:**
    * Extremely low boilerplate for the end-user.
    * Highly declarative: the user just inherits and implements one fixture.
    * Leverages the full power of `pytest`'s fixture system for managing test resources (e.g., database connections, Docker containers).
    * The pattern is intuitive for developers familiar with `pytest`.
* **Negative:**
    * Tightly couples the TCK to the `pytest` framework.
    * It cannot be used with other test runners like `unittest` without significant adaptation.
