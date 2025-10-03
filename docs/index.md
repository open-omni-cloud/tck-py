# Welcome to the Open Omni-Cloud TCK for Python

Certifying the Future of Cloud-Agnostic Computing.

The multi-cloud paradigm promised flexibility but often delivered operational chaos and a new, insidious form of vendor lock-in. The Open Omni-Cloud initiative aims to fix this by replacing marketing ambiguity with a verifiable, engineering-first standard for building truly cloud-agnostic systems.

This project provides the official **Technology Compatibility Kit (TCK)** to make that standard a testable reality.

## What Is This Project?

The Open Omni-Cloud TCK is a ```pytest```-based test suite for the Python ecosystem. Its purpose is to validate and certify that a provider implementation (for services like messaging, storage, or secrets management) adheres to the strict behavioral contracts of the Open Omni-Cloud standard.

A provider that successfully passes this TCK is guaranteed to be a **certified drop-in replacement**, enabling true portability and resilience by design.

## Core Principles

```admonition success
Our philosophy is simple: It's time to stop talking about buzzwords and start building with blueprints.
```

-   **Verifiable Contracts over Vague Promises**: We believe you cannot build what you cannot define and measure. The TCK provides a clear, executable contract for all infrastructure dependencies.

-   **Portability by Design**: A "Truly Omni-cloud" system is not an accident. It is the result of deliberate architectural choices that prioritize clean interfaces and verifiable contracts over abstract, lowest-common-denominator services.

-   **An Open, Community-Driven Ecosystem**: This TCK is an open standard designed to foster an ecosystem of interchangeable providers, giving consumers unprecedented flexibility and dramatically reducing vendor lock-in.

## How to Use This Documentation

This site is organized to help you find what you need quickly.

-   **For Plugin Developers**:
    If you want to build a compliant provider for a cloud service and certify it against the standard, head straight to our `[User Guide](./user-guide/)`.

-   **For Architects**:
    To understand the philosophy, the six pillars of the standard, and the design principles behind the TCK, explore the `[Architecture](./architecture/)` section.

-   **For Contributors**:
    If you want to help improve the TCK by adding new contracts or enhancing existing ones, our `[Contributing](./contributing/)` guide is the place to start.
