# Contributing to the Open Omni-Cloud TCK

First off, thank you for considering contributing! We are thrilled you're interested in helping us build the future of cloud-agnostic computing. Every contribution, from fixing a typo in the documentation to implementing a new contract, is valuable.

This document provides a guide for contributing to the `tck-py` project.

## Code of Conduct

This project and everyone participating in it is governed by our [**Code of Conduct**](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the email address specified in the document.

## How Can I Contribute?

There are many ways to contribute:

-   Reporting bugs
-   Suggesting enhancements or new contracts
-   Improving the documentation
-   Writing code to fix a bug or add a new feature

If you have a substantial change in mind, please **open an issue first** to discuss it with the maintainers.

## Development Setup

To get started with the codebase, follow these steps. This project uses [Poetry](https://python-poetry.org/) for dependency management.

1.  **Fork the repository** on GitHub.

2.  **Clone your fork** locally:
    ```bash
    git clone [https://github.com/open-omni-cloud/tck-py.git](https://github.com/open-omni-cloud/tck-py.git)
    cd tck-py
    ```

3.  **Install dependencies**:
    This project uses dependency groups. The following command will install the main dependencies as well as the development (`dev`) and documentation (`docs`) dependencies.
    ```bash
    poetry install --with dev,docs
    ```

4.  **Activate the virtual environment**:
    ```bash
    poetry shell
    ```
    You are now ready to start coding!

## Running Tests

The TCK is, itself, a test suite. However, it also has its own "meta" test suite to ensure the TCK's internal logic is correct. Before submitting any changes, please ensure that all tests pass.

To run the full test suite:
```bash
pytest
```

## Pull Request Process

1.  Create a new branch for your feature or bug fix:
    ```bash
    git checkout -b feature/my-awesome-feature
    ```

2.  Make your changes. Write clean, readable code.

3.  Ensure the test suite passes with your changes:
    ```bash
    pytest
    ```

4.  Format your commit messages according to our [**Commit Message Guide**](COMMIT_GUIDE.md). This is not just a suggestion; it's a requirement for a clean and automated changelog.

5.  Push your branch to your fork on GitHub:
    ```bash
    git push origin feature/my-awesome-feature
    ```

6.  Open a **Pull Request** from your fork to the `main` branch of the `open-omni-cloud/tck-py` repository.

7.  Provide a clear title and description for your Pull Request, explaining the "what" and "why" of your changes.

Thank you again for your contribution!
