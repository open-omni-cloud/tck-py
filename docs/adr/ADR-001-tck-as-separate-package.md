# ADR-001: TCK as a Separate, Publishable Package

* **Status:** Accepted
* **Date:** 2025-10-03

## Context

The goal of the Open Omni-Cloud initiative is to create an open, verifiable standard for cloud-agnostic providers, not just a testing suite for a single reference implementation (like Fortify). To be a true standard, the TCK must be independent, easily consumable, and decoupled from any specific project that uses it. Alternatives considered included keeping the TCK inside the reference implementation's repository, but this would tightly couple the standard to that single project.

## Decision

We will develop and maintain the TCK in its own dedicated repository (`open-omni-cloud/tck-py`). It will be managed as a standard Python library, published to PyPI, and consumed by provider projects as a development dependency (e.g., via ```poetry add --group dev open-omni-cloud-tck```).

## Consequences

* **Positive:**
    * Reinforces the TCK's role as a public, vendor-neutral standard.
    * Decouples the TCK's versioning and release cycle from any specific provider implementation.
    * Simplifies consumption for third-party provider developers.
    * Allows the standard (the TCK) to be published before a full reference implementation is ready.
* **Negative:**
    * Adds a small amount of overhead, as the TCK is now a dependency to be managed across projects.
