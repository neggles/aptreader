# aptreader AI Coding Guidelines

## Project Overview

aptreader is a **Reflex web application** for browsing APT repository metadata. It downloads, parses, and stores Debian package information (Packages.gz files) from repositories like Ubuntu/Debian mirrors, providing a searchable web interface.

**Core Architecture:**
- **Frontend**: Reflex (Python-based reactive web framework)
- **Backend**: SQLModel/SQLAlchemy with SQLite + Alembic migrations
- **Data Flow**: HTTP fetcher → Debian822 parser → Database → Reflex UI components

## Critical Development Patterns

### Reflex Framework Specifics

**State Management**: All stateful logic lives in `rx.State` subclasses decorated with `@rx.event`:
```python
class AppState(rx.State):
    repositories: list[Repository] = []

    @rx.event
    def load_repositories(self):
        with rx.session() as session:
            self.repositories = list(session.exec(query).all())
```

**Background Operations**: Long-running tasks (fetching, parsing) use `@rx.event(background=True)`:
```python
@rx.event(background=True)
async def fetch_distributions(self, repo_id: int):
    async with self:  # Required for background events
        # Async work with progress updates via self.fetch_progress
```

**Page Routing**: Pages use the `@template()` decorator from `src/aptreader/templates/template.py`:
```python
@template(route="/packages", title="Packages")
def packages_page() -> rx.Component:
    return rx.vstack(...)
```

### Database & Models

**Model Base**: All models inherit from `rx.Model` (SQLModel), not plain SQLModel:
```python
class Repository(rx.Model, table=True):
    name: str = Field(index=True, unique=True)
    distributions: list["Distribution"] = Relationship(...)
```

**Computed Fields**: Use `@computed_field` + `@property` for dynamic data requiring session access:
```python
@computed_field
@property
def repo_distribution_count(self) -> int:
    with rx.session() as session:
        return session.scalar(select(func.count())...)
```

**Many-to-Many Links**: Explicit link tables in `src/aptreader/models/links.py` connect packages to distributions/components/architectures using `link_model` parameter in relationships.

**Sessions**: Always use `with rx.session() as session:` for DB queries. Background events require `async with self` wrapper for state updates.

### Data Fetching & Caching

**Local Mirror Structure**: Downloaded files maintain repo structure under `data/repos/`:
```
data/repos/archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz
```

Implement via `fetcher.url_to_local_path()` which mirrors remote URL structure locally.

**Debian822 Parsing**: Package metadata parsed with `python-debian` library's `deb822.Packages.iter_paragraphs()`. Each paragraph yields a dict-like object with control file fields.

**Progress Reporting**: Background fetchers yield progress updates via state vars (`fetch_progress`, `fetch_message`) checked by frontend polling.

### Configuration & Constants

**Database URL**: Set via `rxconfig.py` which reads from `constants.py`. Alembic migrations (`alembic/env.py`) import DB_URL from rxconfig at runtime.

**Data Directory**: Configurable via `APTREADER_DATA_DIR` env var (default: `./data`). All repos/DB stored there.

**Ordered Lists**: Predefined sort orders for components/architectures in `models/repository.py`:
```python
ORDERED_COMPONENTS = ["main", "contrib", "non-free", ...]
ORDERED_ARCHITECTURES = ["amd64", "arm64", ...]
```

## Development Workflows

**Run Development Server:**
```bash
reflex run  # Auto-reloads on code changes, opens http://localhost:3000
```

**Database Migrations:**
```bash
alembic revision --autogenerate -m "description"  # Generate migration
alembic upgrade head  # Apply migrations
```

**Dependency Management:**
Uses `uv` for builds (see `pyproject.toml` build-backend). Install deps with:
```bash
uv pip install -e ".[dev]"
```

**Code Quality:**
- Linting: `ruff check src/` (configured in pyproject.toml)
- Format: `ruff format src/`
- Target: Python 3.13, 110 char line length

## Critical: Startup Testing Required

**ALWAYS test code changes with `reflex run` before considering work complete.** The app must start without errors. Common startup failures:
- Import errors (e.g., circular imports, missing imports)
- Syntax errors in state event handlers
- Invalid Reflex component syntax
- Database migration issues
- Model definition errors

If `reflex run` exits with errors, the change is incomplete and must be fixed.

## Common Pitfalls

1. **Don't forget `async with self`** in `@rx.event(background=True)` when updating state
2. **Import order matters**: Reflex must be imported before models that use `rx.Model`
3. **Session context**: Never pass SQLModel instances across sessions - query fresh in each scope
4. **Component sorting**: Use `format_components`/`format_architectures` computed fields, not raw lists

## Key Files Reference

- `src/aptreader/backend/backend.py` - Main `AppState` with all event handlers
- `src/aptreader/fetcher.py` - HTTP fetching, Release/Packages.gz parsing
- `src/aptreader/models/` - Database schema (repository.py, packages.py, links.py)
- `src/aptreader/templates/template.py` - Page wrapper with sidebar, theme state
- `rxconfig.py` - Reflex app configuration (DB URL, plugins)
- `alembic/env.py` - Migration runner that imports rxconfig DB settings
