# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

```info
This changelog is automatically generated from commit messages that follow the [Conventional Commits](COMMIT_GUIDE.md) standard. Please do not edit it manually.
```

## [Unreleased]

### Added
-   Initial project setup with Poetry.
-   Created TCK contracts for Primitives (`kv_store`, `secrets`, `object_storage`, `cache`, `document_database`).
-   Created TCK contracts for Messaging (`producer`, `consumer`, `delayed_messaging`).
-   Created TCK contracts for Resilience (`transactional_outbox`, `sagas`, `distributed_lock`, `circuit_breaker`).
-   Created TCK contracts for Observability (`tracing`, `metrics`, `logging`).
-   Created TCK contracts for Policies and Security (`multi_tenancy`, `iam`).
-   Established core documentation structure with MkDocs, including initial User Guides.
-   Established community documents (`CODE_OF_CONDUCT`, `CONTRIBUTING`, `SECURITY`, `ARCHITECTURE`).

### Changed
-   Refactored TCK to use a centralized `shared` module for models and exceptions (ADR-004).

### Fixed
-   *(Nothing yet)*

---

*(Future releases will appear here, e.g., ## [0.1.0] - YYYY-MM-DD)*
