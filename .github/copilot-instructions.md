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
src/aptreader/          # Main application package (FastAPI backend)
├── __init__.py
└── app.py              # Entry point with main() function
frontend/               # Vite-based frontend (to be added)
```

## Key Conventions

### Entry Point
The console script `aptreader` is defined in `pyproject.toml` and maps to `aptreader.app:app`.
CLI functionality should be implemented using **Typer** through this entry point.

### Dependencies
- Runtime dependencies go in `[project.dependencies]`
- Dev tools (ruff, etc.) go in `[dependency-groups.dev]`
- Use uv commands to modify dependencies rather than editing `pyproject.toml` manually

### Code Style
- Use double quotes for strings (enforced by ruff)
- Line length limit: 110 characters
- Follow ruff's flake8-bugbear rules for common bug patterns

## Architecture

### CLI: Typer
Command-line interface built with Typer for repository management and server control.

### Backend: FastAPI
The web API will be built with FastAPI. The backend handles:
- Downloading APT repository metadata to local per-repo directories
- Parsing repository files using Python libraries (APT itself is Python-based)
- Serving parsed data via REST API
- Dependency tree analysis and repository structure navigation

### Frontend: Vite
A separate Vite-based frontend will provide the UI for:
- Repository browsing and navigation
- Package detail views
- Dependency visualization

### APT Repository Handling
- **Local caching**: Each repository's metadata is downloaded to a per-repo directory
- **Parser libraries**: Use existing Python APT parsing libraries (e.g., `python-apt`, `python-debian`) rather than implementing custom parsers
- **Repository structure**: Support standard APT repository layouts with releases, components, and architectures
- **Metadata files**: Handle Packages files, Release files, and InRelease signatures

### Data Flow
1. User provides APT repository URL (e.g., `http://archive.ubuntu.com/ubuntu`)
2. Backend downloads and caches metadata files locally
3. Python APT libraries parse the Debian control file format
4. FastAPI serves structured data to frontend
5. Frontend displays repository tree, package details, and dependency graphs
