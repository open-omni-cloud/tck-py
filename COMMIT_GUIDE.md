# Commit Message Guide

This project follows the [**Conventional Commits**](https://www.conventionalcommits.org/en/v1.0.0/) specification. Adhering to this guide is a requirement for all contributions, as it allows us to automate versioning and changelog generation.
## Format

Each commit message consists of a **header**, a **body**, and a **footer**.
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

The header is mandatory and has a specific format: `<type>(<scope>): <description>`.
---

### Type

The `<type>` must be one of the following:

-   **feat**: A new feature for the user (correlates with `MINOR` in semantic versioning).
-   **fix**: A bug fix for the user (correlates with `PATCH` in semantic versioning).
-   **docs**: Changes to documentation only (`README`, user guides, etc.).
-   **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc).
-   **refactor**: A code change that neither fixes a bug nor adds a feature.
-   **perf**: A code change that improves performance.
-   **test**: Adding missing tests or correcting existing tests.
-   **build**: Changes that affect the build system or external dependencies (example scopes: `poetry`, `github-actions`).
-   **ci**: Changes to our CI configuration files and scripts.
-   **chore**: Other changes that don't modify `src` or `test` files (e.g., updating `.gitignore`).
---

### Scope (Optional)

The `<scope>` provides additional contextual information. It's a noun describing the section of the codebase the commit affects.
-   Examples: `primitives`, `messaging`, `resilience`, `observability`, `sagas`, `kv_store`, `ci`, `docs`.
---

### Description

The `<description>` contains a succinct description of the change:

-   Use the imperative, present tense: "change" not "changed" nor "changes".
-   Don't capitalize the first letter.
-   No dot (`.`) at the end.
---

### Body (Optional)

The `<body>` is used to provide additional context, such as the motivation for the change and contrast with previous behavior.
---

### Footer (Optional)

The `<footer>` is used to reference issues or to signal breaking changes.

**Breaking Change (Breaking Change: or !):**

A change that introduces backward-incompatible changes to the Public API (correlates with `MAJOR` in semantic versioning). A breaking change **must** be signaled in one of two ways:

1.  **Footer (Classic)**: A footer beginning with `BREAKING CHANGE:` introduces a breaking API change.

    ```
    BREAKING CHANGE: The `provider_factory` fixture for the messaging contracts now returns a tuple of three items instead of two.
    ```
2.  **Header (Recommended)**: Append a `!` (exclamation mark) directly after the `type` or `scope` in the header.

    ```
    refactor(messaging)!: update consumer fixture return signature
    ```

A `BREAKING CHANGE` can be part of any `type`.

---

## Examples

### Commit with a scope and a body

```
feat(primitives): add document_database contract

Introduces the `TestDocumentDatabaseContract` to validate low-level
CRUD operations for document-oriented databases. This provides the
foundational layer for more complex persistence providers.
```

### Commit with a breaking change (using the recommended header syntax)

```
refactor(messaging)!: update consumer fixture to support DLQ tests

The `provider_factory` for `TestConsumerContract` now returns a tuple of
three items (`consumer_task`, `publish_func`, `get_message_from_dlq`)
instead of two. This is required to enable verification of the DLQ
resilience pattern.
BREAKING CHANGE: The return signature of the consumer `provider_factory` has changed.
All provider implementations must be updated to return the new `get_message_from_dlq` function.
```

### Simple fix

```
fix(docs): correct typo in README getting started guide
```
