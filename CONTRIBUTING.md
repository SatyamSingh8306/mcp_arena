# Contributing to mcp_arena

Thank you for your interest in contributing to mcp_arena! This document provides guidelines and instructions for contributing to this project.

> 👉 **Before you begin:** Please read our [⚖️ Code of Conduct](CODE_OF_CONDUCT.md) to understand our community standards and expectations.

## 📚 Table of Contents

- [⚖️ Code of Conduct](#️-code-of-conduct)
- [🚀 Getting Started](#-getting-started)
- [🛠️ Development Setup](#️-development-setup)
- [✨ Making Contributions](#-making-contributions)
- [📤 Pull Request Process](#-pull-request-process)
- [📐 Coding Standards](#-coding-standards)
- [✅ Testing Guidelines](#-testing-guidelines)
- [📚 Documentation](#-documentation)
- [🎯 Priority Areas](#-priority-areas)
- [👥 Community](#-community)

## ⚖️ Code of Conduct

This project and everyone participating in it is governed by our [⚖️ Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [satyamsingh8306@gmail.com](mailto:satyamsingh8306@gmail.com).

Key principles:
- 🤝 Be respectful and considerate in all interactions
- 👋 Welcome newcomers and help them get started
- 💬 Focus on constructive feedback
- 🎯 Accept responsibility for your mistakes and learn from them
- 🌈 Foster an inclusive and harassment-free environment

For full details, please read the [⚖️ complete Code of Conduct](CODE_OF_CONDUCT.md).

## 🚀 Getting Started

### 📦 Prerequisites

- Python 3.12 or higher
- Git
- A GitHub account

### 🍴 Fork and Clone

1. **Fork the repository** on GitHub by clicking the "Fork" button
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mcp_arena.git
   cd mcp_arena
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/SatyamSingh8306/mcp_arena.git
   ```

## 🛠️ Development Setup

### 📦 Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

### 💿 Install Dependencies

```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Or install all optional dependencies
pip install -e ".[complete]"
```

### ✅ Verify Installation

```bash
# Run tests to verify setup
pytest

# Check imports
python -c "import mcp_arena; print(f'Version: {mcp_arena.__version__}')"
```

## ✨ Making Contributions

### 🌳 Branch Naming Convention

Create a new branch for each contribution:

```bash
# Sync with upstream first
git checkout main
git pull upstream main

# Create your feature branch
git checkout -b <type>/<short-description>
```

Branch types:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes
- `chore/` - Maintenance tasks

Examples:
- `feature/add-azure-preset`
- `fix/memory-leak-in-agent`
- `docs/update-installation-guide`

### 📝 Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

<optional body>

<optional footer>
```

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Code style (formatting, etc.)
- `refactor` - Code refactoring
- `test` - Tests
- `chore` - Maintenance

Examples:
```bash
git commit -m "feat(agent): add run() method to ReactAgent"
git commit -m "fix(memory): add timestamps to conversation turns"
git commit -m "docs: add API documentation for presets"
```

## 📤 Pull Request Process

### 🔍 Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests**:
   ```bash
   pytest
   ```

3. **Run linting**:
   ```bash
   flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
   ```

4. **Format code** (optional but recommended):
   ```bash
   black .
   isort .
   ```

### 📨 Submitting Your PR

1. Push your branch to your fork:
   ```bash
   git push origin your-branch-name
   ```

2. Open a Pull Request on GitHub

3. Fill out the PR template with:
   - Clear description of changes
   - Related issue numbers (if any)
   - Testing performed
   - Screenshots (for UI changes)

### 👀 PR Review Process

- Maintainers will review your PR
- Address any requested changes
- Once approved, your PR will be merged

## 📐 Coding Standards

### 🐍 Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Use [Black](https://github.com/psf/black) for formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Maximum line length: 127 characters

### 🏷️ Type Hints

Use type hints for function signatures:

```python
def process(self, input_data: Any) -> Any:
    """Process input and return response."""
    pass
```

### 📝 Docstrings

Use docstrings for all public classes and methods:

```python
def add_tool(self, tool: IAgentTool) -> None:
    """Add a tool to the agent.
    
    Args:
        tool: The tool to add to this agent
        
    Returns:
        None
    """
    self.tools.append(tool)
```

### 🏛️ SOLID Principles

This project follows SOLID principles:

- **Single Responsibility**: Each class has one clear purpose
- **Open/Closed**: Extensible through interfaces and inheritance
- **Liskov Substitution**: Implementations can substitute their interfaces
- **Interface Segregation**: Focused, cohesive interfaces
- **Dependency Inversion**: Depend on abstractions, not concretions

## ✅ Testing Guidelines

### 🏃 Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_agents.py

# Run specific test
pytest tests/test_agents.py::TestAgentInitialization::test_react_agent_init

# Run with coverage
pytest --cov=mcp_arena
```

### ✍️ Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Name test functions with `test_` prefix
- Use descriptive test names

Example:
```python
class TestAgentInitialization:
    """Tests for agent initialization."""
    
    def test_react_agent_init(self):
        """Test ReactAgent initializes correctly."""
        agent = ReactAgent()
        assert agent is not None
        assert hasattr(agent, 'process')
```

## 📚 Documentation

### 📍 Where to Add Documentation

- **README.md** - Project overview and quick start
- **docs/** - Detailed documentation
  - `INSTALLATION.md` - Installation instructions
  - `QUICKSTART.md` - Getting started guide
  - `AGENT_GUIDE.md` - Agent system documentation
  - `TOOLS_GUIDE.md` - Tools documentation
  - `MCP_SERVERS_GUIDE.md` - MCP servers documentation

### ✍️ Documentation Style

- Use clear, concise language
- Include code examples
- Keep documentation up to date with code changes

## 🎯 Priority Areas

We especially welcome contributions in these areas:

| Area | Description |
|------|-------------|
| **New Presets** | Add MCP server presets for new platforms |
| **Agent Improvements** | Enhance agent patterns and capabilities |
| **Documentation** | Improve docs, add examples, fix typos |
| **Bug Fixes** | Fix issues and improve stability |
| **Performance** | Optimize code performance |
| **Tests** | Increase test coverage |

## 👥 Community

### ⚖️ Code of Conduct

All community interactions are governed by our [⚖️ Code of Conduct](CODE_OF_CONDUCT.md). Please read and follow it to help maintain a welcoming and inclusive environment.

### 🎓 Getting Help

- Open a [GitHub Issue](https://github.com/SatyamSingh8306/mcp_arena/issues) for bugs
- Use [GitHub Discussions](https://github.com/SatyamSingh8306/mcp_arena/discussions) for questions
- Check existing issues before creating new ones

### 🐛 Reporting Bugs

When reporting bugs, include:

1. Python version (`python --version`)
2. mcp_arena version (`pip show mcp-arena`)
3. Operating system
4. Steps to reproduce
5. Expected vs actual behavior
6. Error messages/stack traces

> ⚠️ **Security Issues:** If you discover a security vulnerability, please do NOT open a public issue. Instead, follow our [Security Policy](SECURITY.md) for responsible disclosure.

### 💡 Feature Requests

For feature requests:

1. Check if it already exists in issues
2. Describe the use case
3. Explain why it would benefit the project

---

## 🔗 Related Documentation

- 📖 **[README](README.md)** - Project overview and quick start
- ⚖️ **[Code of Conduct](CODE_OF_CONDUCT.md)** - Community guidelines
- 🔒 **[Security Policy](SECURITY.md)** - Security and vulnerability reporting
- 📜 **[License](LICENSE)** - MIT License details

---

## Thank You! 🙏

Thank you for contributing to mcp_arena! Your contributions help make this project better for everyone.

If you have questions, don't hesitate to ask. We're here to help!

**Happy Contributing!** 🚀
