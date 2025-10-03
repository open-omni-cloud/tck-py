# Architecture Decisions

This document provides an overview and index of the Architecture Decision Records (ADRs) for the **Open Omni-Cloud TCK (`tck-py`)** project.

## What is an ADR?

An Architecture Decision Record (ADR) is a short, immutable document that describes a single, significant architectural decision. We use ADRs to document the "why" behind our technical choices, providing context and rationale for future contributors and maintainers.

Each ADR is stored as a separate file in the `docs/adr/` directory.

## ADR Index

| ADR                                                                   | Title                                                 |
| --------------------------------------------------------------------- | ----------------------------------------------------- |
| [ADR-001](./adr/ADR-001-tck-as-separate-package.md)                 | TCK as a Separate, Publishable Package                |
| [ADR-002](./adr/ADR-002-pytest-contract-inheritance-and-fixtures.md)  | Pytest-based Contract Inheritance with Fixture Injection |
| [ADR-003](./adr/ADR-003-mixin-classes-for-policy-contracts.md)          | Use of Mixin Classes for Policy Contracts             |
| [ADR-004](./adr/ADR-004-centralized-shared-module.md)                   | Centralized `shared` Module for Core Entities        |
