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
src/aptreader/              # Main application package
├── __init__.py
├── aptreader.py            # Main Reflex app and Typer CLI entry point
├── state.py                # Application state (Reflex State class)
├── models.py               # Data models (Pydantic dataclasses)
├── repository.py           # Repository download/parsing logic
├── pages/
│   └── index.py            # Main page component (Reflex)
├── templates/              # App-wide layout and theming (if present)
```

## Key Conventions

### Entry Point
The console script `aptreader` is defined in `pyproject.toml` and maps to `aptreader.aptreader:main`.
The Reflex app is initialized in `aptreader.py` and runnable via `reflex run`.

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
The application is built with **Reflex** (https://reflex.dev), a pure-Python full-stack framework for both backend logic and frontend UI.

- **Main app**: `aptreader.py` defines the Reflex app
- **State management**: `state.py` contains the Reflex State class for all app state
- **Pages**: UI components and pages are organized under `pages/` (e.g., `pages/index.py`)
- **Repository logic**: Downloading, parsing, and caching handled in `repository.py` using `httpx` and `python-debian`
- **Models**: Data models defined in `models.py` using Pydantic dataclasses
- **No Node.js required**: Reflex compiles frontend automatically

### APT Repository Handling
* **Local caching**: Each repository's metadata is downloaded to a per-repo directory in `<repo_root>/.cache/aptreader/`
* **Parser libraries**: Uses `python-debian` for parsing Debian control files
* **Repository structure**: Supports standard APT repository layouts with releases, components, and architectures
* **Metadata files**: Handles Packages files, Release files, and InRelease signatures

### Data Flow
1. User provides APT repository URL via Reflex UI
2. RepositoryManager downloads and caches metadata files locally
3. `python-debian` parses the Debian control file format
4. Reflex State updates trigger reactive UI changes
5. Reflex components display repository tree, package details, and dependency graphs
