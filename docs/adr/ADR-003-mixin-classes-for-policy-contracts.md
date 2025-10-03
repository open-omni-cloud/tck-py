# ADR-003: Use of Mixin Classes for Policy Contracts

* **Status:** Accepted
* **Date:** 2025-10-03

## Context

Some TCK contracts represent cross-cutting concerns or policies (like Multi-Tenancy) that should be applicable to multiple primitive providers (e.g., a KV Store, an Outbox Repository). Using a simple inheritance model would lead to code duplication (e.g., re-implementing tenancy tests for each storage type) or a complex, unmanageable class hierarchy.

## Decision

We will define policy-based contracts as **mixin classes** (e.g., `TestMultiTenancyContractMixin`). Provider developers can then create a compliance suite by inheriting from both a primitive contract and a policy mixin (e.g., ```class TestMyProvider(TestKVStoreContract, TestMultiTenancyContractMixin):```). This allows for a compositional approach to building test suites.

## Consequences

* **Positive:**
    * Promotes extreme code reuse. The multi-tenancy tests are written once and can be applied to any persistence provider.
    * Highly composable and flexible architecture for the TCK.
    * Keeps concerns cleanly separated.
* **Negative:**
    * Requires the provider developer to understand and use multiple inheritance in Python.
    * The fixture implementation becomes more complex, as it must satisfy the requirements of all inherited contracts (e.g., supporting the `tenant_id` parameter).
