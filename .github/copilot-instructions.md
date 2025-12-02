# aptreader Copilot Instructions

## Project Overview

aptreader is a web application for downloading and browsing APT repository metadata, packages, and files. It allows users to point at an APT repository URL (like `http://archive.ubuntu.com/ubuntu`) to download Packages files, parse them, and browse distribution releases, components, packages, and their details.

**Current Status**: Early development - project structure and tooling established, core functionality not yet implemented.

## Development Environment

### Package Management: uv
This project uses [uv](https://github.com/astral-sh/uv) for dependency management and builds.

- **Install dependencies**: `uv sync`
- **Run the app**: `uv run aptreader` (executes `aptreader.app:main`)
- **Add dependencies**: `uv add <package>` for runtime, `uv add --dev <package>` for dev tools
- **Python version**: 3.13+ (specified in `.python-version`)

### Code Quality

- **Linter/Formatter**: ruff (configured in `pyproject.toml`)
  - Line length: 110 characters
  - Target: Python 3.13
  - Enabled rules: E4, E7, E9, F (pyflakes), B (flake8-bugbear)
  - Ignored: E501 (line length), I001 (import order), B905 (zip strict)
  - Inline quotes: double quotes
- **Type Checking**: Enabled with `python.analysis.typeCheckingMode: "basic"` in VS Code

## Project Structure

```
src/aptreader/          # Main application package
├── __init__.py
└── app.py              # Entry point with main() function and Reflex app
```

## Key Conventions

### Entry Point
The console script `aptreader` is defined in `pyproject.toml` and maps to `aptreader.app:main`.
CLI functionality should be implemented using **Typer** through this entry point.
The Reflex app should be initialized in `aptreader.app` and runnable via the CLI.

### Dependencies
- Runtime dependencies go in `[project.dependencies]`
- Dev tools (ruff, etc.) go in `[dependency-groups.dev]`
- Use uv commands to modify dependencies rather than editing `pyproject.toml` manually

### Code Style
- Use double quotes for strings (enforced by ruff)
- Line length limit: 110 characters
- Follow ruff's flake8-bugbear rules for common bug patterns

## Architecture

### Web Framework: Reflex
The application is built with **Reflex** (https://reflex.dev), a pure-Python full-stack framework that handles both backend logic and frontend UI.

- **Backend logic**: Repository downloading, parsing, caching, and data management in Python
- **Frontend UI**: Reflex components for interactive web interface (compiles to React but written in Python)
- **State management**: Reflex's built-in state system for reactive UI updates
- **No separate Node.js required**: Reflex handles all frontend compilation

### CLI: Typer
Command-line interface built with Typer for:
- Starting/stopping the Reflex web server
- Repository management operations
- Configuration and setup tasks

### APT Repository Handling
- **Local caching**: Each repository's metadata is downloaded to a per-repo directory
- **Parser libraries**: Use existing Python APT parsing libraries (e.g., `python-apt`, `python-debian`) rather than implementing custom parsers
- **Repository structure**: Support standard APT repository layouts with releases, components, and architectures
- **Metadata files**: Handle Packages files, Release files, and InRelease signatures

### Data Flow
1. User provides APT repository URL via Reflex UI
2. Backend logic downloads and caches metadata files locally
3. Python APT libraries parse the Debian control file format
4. Reflex state updates trigger reactive UI changes
5. Reflex components display repository tree, package details, and dependency graphs
