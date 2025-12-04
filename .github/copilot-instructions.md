# aptreader Development Guide

## Project Overview

aptreader is a Reflex web application for downloading, parsing, and browsing APT repository metadata. It downloads Packages files from APT repositories (e.g., Ubuntu/Debian mirrors), parses them using python-debian, and provides a web UI to browse repositories, distributions, components, and packages.

## Architecture

### Database Models & APT Repository Integration

The app uses SQLModel database models to store repository and distribution metadata:

1. **Database Models** (`backend/backend.py`):
    - `Repository(rx.Model)`: Stores repo URL, name, update timestamp
    - `Distribution(rx.Model)`: Stores release metadata (codename, suite, architectures, components, raw Release file text)
    - Foreign key relationship: `Distribution.repository_id -> Repository.id` with cascade delete
    - Uses SQLite via `rx.session()` context managers

2. **Repository Fetching** (`fetcher.py`):
    - `discover_distributions()`: Probes common distribution names at a repo URL
    - `fetch_release_file()`: Downloads and parses individual Release files
    - `fetch_distributions()`: Main function - discovers and fetches all distributions
    - Files cached at `REPOS_DIR/{domain}/{path}` mirroring source structure
    - Progress callbacks for UI feedback during long operations

3. **Legacy Code** (ignore these):
    - `models/package.py`: Pydantic models from earlier iteration (not yet integrated)
    - `repository.py`: Old RepositoryManager implementation (not currently used)
    - `temp/oldfiles/`: Previous attempt code

### State Management with Reflex

-   `State(rx.State)` in `backend/backend.py` handles all application state and database operations
-   State methods decorated with `@rx.event` are event handlers called from UI components
-   State attributes automatically trigger UI re-renders when modified
-   Common pattern: Load data in event handlers, update state attributes, return toast notifications
    ```python
    @rx.event
    def load_repositories(self) -> rx.event.EventSpec:
        with rx.session() as session:
            self.repositories = session.exec(query).all()
        return rx.toast.success("Loaded successfully.")
    ```

### Template System

-   `templates/template.py` provides the `@template` decorator for consistent page layouts
-   Wraps pages with sidebar, theme configuration, and metadata
-   All pages use: `@template(route="/", title="...")` then return components
-   Theme customization via `ThemeState` (accent color, gray color, radius, scaling)
-   Sidebar defined in `components/sidebar.py` with automatic active link highlighting

## Key Developer Workflows

### Running the Development Server

```bash
reflex run         # Start dev server (default: localhost:3000)
# Or with custom API URL (see .envrc for environment config)
```

The app uses `.envrc` for environment configuration (direnv integration):

-   `REFLEX_API_URL`: Backend API endpoint
-   `REFLEX_LOGLEVEL`: Logging verbosity
-   Virtual environment automatically activated via direnv

### Database Migrations

```bash
# Database is SQLite (aptreader.db) managed by Alembic
reflex db makemigrations "description"  # Generate migration
reflex db migrate                       # Apply migrations
```

-   Migration scripts in `alembic/versions/`
-   Config in `alembic.ini` (timezone set to UTC)
-   DB URL configured in `rxconfig.py` via `APTREADER_DB_URL` env var (default: `sqlite:///aptreader.db`)

### Cache Directory Structure

Repository metadata is cached in `data/repos/` (configurable via `APTREADER_DATA_DIR` env var):
- Path structure mirrors source: `data/repos/{domain}/{path}/dists/{dist}/Release`
- Example: `https://archive.kylinos.cn/dists/10.0/Release` → `data/repos/archive.kylinos.cn/dists/10.0/Release`
- See `constants.REPOS_DIR` and `fetcher.url_to_local_path()` for path conversion
- Files are downloaded once and reused; re-fetching a repo replaces existing distributions in DB

### Code Quality

```bash
ruff check .       # Lint with ruff (configured in pyproject.toml)
ruff format .      # Auto-format code
```

-   Target: Python 3.13
-   Line length: 110 characters
-   Uses flake8-bugbear rules, double quotes enforced

## Project-Specific Conventions

### Component Patterns

1. **Dialog Forms**: Standardized add/edit pattern in `views/repositories.py`

    - Green archive badge + title/description header
    - `form_field()` helper from `components/form_field.py` for consistent input styling
    - Dialog trigger -> Dialog content with rx.form.root -> Submit/Cancel buttons
    - Forms call State event handlers (`add_repository_to_db`, `update_repository_in_db`)

2. **Table Views**:
    - `show_repository()` function renders table rows with `rx.table.row/cell`
    - Actions column contains: view distributions (list icon), fetch distributions (download icon), edit, delete
    - Green download button triggers `State.fetch_repository_distributions()` with loading indicator
    - Sort/filter/search controls in `rx.flex` above table
    - Table uses `on_mount=State.load_entries` to load data on page load

3. **Progress Indicators**: Long-running async operations must show feedback
    - `State.is_fetching` + `State.fetch_message`: Boolean flag and progress message
    - Display with `rx.callout` containing `rx.spinner` and progress text
    - Update progress via callback passed to async functions
    - Example in `views/repositories.py` for distribution fetching

3. **Event Handler Pattern**:
    ```python
    on_click=lambda: State.delete_repository_from_db(repo.id)  # Pass params via lambda
    on_click=State.toggle_sort  # No-param handlers called directly

    # For conditional handlers (when param might be None)
    on_click=State.handler(repo.id) if repo.id else rx.noop
    ```

4. **Async Generators for Progress**: Use `yield` for incremental UI updates in long operations
    ```python
    @rx.event
    async def long_operation(self):
        self.is_loading = True
        self.progress = "Step 1..."
        yield  # Updates UI

        await some_async_work()

        self.progress = "Step 2..."
        yield  # Updates UI again

        self.is_loading = False
        yield rx.toast.success("Done!")  # Final update
    ```

### Styling System

-   Centralized styles in `styles.py` using Reflex color system
-   Uses CSS variables: `rx.color("gray", 3)`, `rx.color("accent", 10)`
-   Common styles: `accent_text_color`, `gray_bg_color`, `border_radius`
-   Theme customization via `ThemeState` accessible across all pages
-   Hover effects defined inline: `style={"_hover": {"bg": rx.color("gray", 3)}}`

### APT Repository Parsing with python-debian

**Implementation Guide** (see `temp/deb822_test.py` for reference):

```python
from debian import deb822
import httpx

# Download Release file
async with httpx.AsyncClient() as client:
    response = await client.get(f"{repo_url}/dists/{dist}/Release")
    release_text = response.text

# Parse with python-debian
release_data = deb822.Release(release_text)

# Access fields like a dict:
# - release_data["Origin"], release_data["Suite"], release_data["Codename"]
# - release_data["Architectures"].split()  # Space-separated list
# - release_data["Components"].split()     # Space-separated list
# - release_data["Date"]                   # Parse with dateutil.parser
```

**Cache files** in `data/` directory (configurable via `APTREADER_CACHE_DIR` env var) to avoid repeated downloads.

## File Structure Quick Reference

```
src/aptreader/
├── backend/backend.py       # State + SQLModel database models + fetch logic
├── fetcher.py               # APT repo discovery and Release file downloading
├── constants.py             # DATA_DIR, REPOS_DIR, DB_URL configuration
├── models/package.py        # Legacy Pydantic models (not integrated)
├── repository.py            # Legacy RepositoryManager (unused)
├── templates/template.py    # Page wrapper decorator + ThemeState
├── components/              # Reusable UI components
│   ├── sidebar.py          # Navigation sidebar
│   ├── form_field.py       # Standardized form inputs
│   └── logo.py             # App logo component
├── views/repositories.py    # Repository table + CRUD dialogs
└── pages/
    ├── index.py            # Main repositories page
    └── distributions.py    # Distribution listing page (dynamic route)
```

## Dependencies & Setup

**Getting Started**:

```bash
uv venv           # Create virtual environment
uv sync           # Install dependencies from uv.lock
reflex run        # Start development server
```

**Key Dependencies**:

-   **Reflex**: Full-stack Python framework (state management, routing, components)
-   **SQLModel**: Database ORM (via `rx.Model`)
-   **python-debian**: Parses APT Packages/Release files (deb822 format)
-   **httpx**: Async HTTP client for downloading repo files
-   **Pydantic**: Data validation for domain models
-   **uv**: Fast Python package manager

## Common Pitfalls & Best Practices

1. **State immutability**: Reflex state changes must assign new values, not mutate in-place (e.g., `self.repos = new_list` not `self.repos.append()`)
2. **Session context**: Always use `with rx.session() as session:` for database operations
3. **Lambda bindings**: Event handlers with parameters need lambda wrappers: `on_click=lambda: handler(arg)`
4. **Async event handlers**: State methods can be async when downloading/parsing repo data:
   ```python
   @rx.event
   async def fetch_distributions(self, repo_id: int):
       async with httpx.AsyncClient() as client:
           # Download and parse Release files
       with rx.session() as session:
           # Save to database
       yield rx.toast.success("Distributions loaded")
   ```
5. **Progress feedback required**: Never start long-running operations without UI feedback - use loading states and progress messages
6. **Ignore temp directories**: `temp/oldfiles/` contains abandoned code from previous iterations

## Current Development Status

**Completed Features**:
- Repository CRUD operations with database persistence
- Distribution discovery via probing common codenames (Ubuntu, Debian)
- Release file downloading and parsing with python-debian
- Progress indicators for async operations
- Distributions page to view fetched distributions

**Next Features** (not yet implemented):
- Download package lists (Packages.gz files) for distributions/components
- Parse and display individual packages
- Package search and filtering
- Download actual .deb package files
        async with httpx.AsyncClient() as client:
            # Download and parse Release files
        with rx.session() as session:
            # Save to database
        return rx.toast.success("Distributions loaded")
    ```
5. **Ignore temp directories**: `temp/oldfiles/` contains abandoned code from previous iterations

## Current Development Focus

**Next Feature**: Implement distribution discovery and population

-   Add State event handler to fetch all distributions from a repository URL
-   Download Release files from common distribution names (jammy, focal, bookworm, etc.)
-   Parse with `debian.deb822.Release()` (see `temp/deb822_test.py`)
-   Create `Distribution` records in database linked to parent `Repository`
-   Add UI button/action to trigger distribution fetch for a repository
-   Display distributions in a nested table or expandable row under each repository
