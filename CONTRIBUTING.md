# Contributing to mcp_arena

Thanks for your interest in contributing. This document covers the development setup and the conventions used in this repository.

## Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Requests](#pull-requests)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

Be respectful and constructive. Welcome newcomers, give actionable feedback, and take responsibility for mistakes.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/mcp_arena.git
   cd mcp_arena
   ```

3. Add the upstream remote:

   ```bash
   git remote add upstream https://github.com/SatyamSingh8306/mcp_arena.git
   ```

## Development Setup

Create and activate a virtual environment, then install the project with development dependencies:

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

Use `.[complete]` instead if you need every preset extra as well. Verify the setup:

```bash
pytest
python -c "import mcp_arena; print(mcp_arena.__version__)"
```

## Making Changes

Create one branch per contribution:

```bash
git checkout main
git pull upstream main
git checkout -b <type>/<short-description>
```

Common prefixes are `feature/`, `fix/`, `docs/`, `refactor/`, `test/`, and `chore/`.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

<optional body>

<optional footer>
```

For example: `feat(presents): add Azure MCP server preset` or `docs: update extras reference`.

## Pull Requests

Before opening a PR, sync with upstream and run the test and lint checks:

```bash
git fetch upstream
git rebase upstream/main
pytest
ruff check .
black .
isort .
```

Describe what changed and why, link any related issues, and note the tests you ran. Maintainers will review the PR and may request changes before merging.

## Coding Standards

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Format with Black and sort imports with isort (line length 100).
- Add type hints to public functions and methods.
- Write docstrings for public classes and functions.
- Keep each preset self-contained in `mcp_arena/presents/<name>.py` and declare its optional dependencies in `_REQUIRED_EXTRAS`.

## Testing

```bash
pytest
pytest -v
pytest tests/test_make_mcp_agent.py
pytest tests/test_sentry.py::test_sentry_tools_use_configured_api_and_bound_limits
```

Place tests in `tests/`, prefix files and functions with `test_`, and keep each test focused on one behavior. New presets should include a test that verifies tool registration and configuration handling.

## Documentation

- `README.md` — project overview and quick start
- `CONTRIBUTING.md` — this document
- `CHANGELOG.md` — version history and migration guides
- `docs/` — installation, quick start, MCP servers, tools, agents, and tutorials

Keep documentation in sync with code changes, especially when a preset's extra, credentials, or transport behavior changes.

## Reporting Issues

Include the following when reporting a bug:

1. Python version (`python --version`)
2. `mcp_arena` version (`pip show mcp-arena`)
3. Operating system
4. Steps to reproduce
5. Expected and actual behavior
6. Full error message or traceback

For feature requests, describe the use case and check existing issues first.
