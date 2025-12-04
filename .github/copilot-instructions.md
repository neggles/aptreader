````instructions
# aptreader Copilot Guide

## Architecture Snapshot
- Reflex app lives in `src/aptreader`; `backend/backend.py` defines both the persisted models (`Repository`, `Distribution`) via `rx.Model`/SQLModel and the main `State(rx.State)` event hub.
- `fetcher.py` owns remote APT access: it probes common distro names, downloads Release files with `httpx`, parses them using `debian.deb822`, and writes mirrors into `constants.REPOS_DIR` (`data/repos/...`).
- Pages (`pages/index.py`, `pages/distributions.py`) are thin wrappers that call view helpers in `views/` and rely on `templates/template.py` for consistent layout + theme (`ThemeState`, sidebar injection).
- UI widgets (table rows, dialogs) are organized under `components/` and `views/`; legacy files in `models/package.py`, `repository.py`, and `temp/` are intentionally unused.

## State & Events
- Every DB touch happens inside `with rx.session() as session:`; always assign new lists/values on state mutations to trigger Reflex reactivity.
- Event handlers that need parameters must be wrapped (e.g., `on_click=lambda: State.delete_repository_from_db(repo.id)`); parameterless handlers can be referenced directly.
- Long-running handlers (fetching repos) are async generators: toggle `State.is_fetching`/`State.fetch_message`, `yield` after each stage to refresh the UI, and finish with a toast (`rx.toast.success`).
- When adding fetch steps, update both the DB rows and cached filesystem artifacts so repeated runs remain idempotent.

## UI Patterns
- Repository CRUD/dialog flows live in `views/repositories.py`; dialogs use the shared `components/form_field.form_field()` helper plus `rx.form.root` submit/cancel controls.
- Tables are built with `rx.table.*` inside `show_repository()`; action buttons follow the icon + tooltip pattern already used for “view distributions”, “fetch distributions”, “edit”, “delete”.
- Loading/progress feedback appears as `rx.callout` blocks with `rx.spinner` bound to `State.is_fetching`; never launch a download without showing that callout.
- Sidebar (`components/sidebar.py`) automatically highlights the active route using `rx.cond` and theme colors from `styles.py`; match those tokens when adding navigation.

## Data & Caching
- Cache layout mirrors upstream URLs: `data/repos/{domain}/{path}/dists/{dist}/Release`; `constants.url_to_local_path()` already handles the mapping—reuse it.
- Environment variables (`APTREADER_DATA_DIR`, `APTREADER_DB_URL`, `REFLEX_API_URL`, `REFLEX_LOGLEVEL`) are loaded via `.envrc`; use them instead of hardcoding paths.
- SQLite DB (`aptreader.db`) is managed through Alembic; migrations live under `alembic/versions/` and cascade delete is expected between `Repository` and `Distribution`.

## Developer Workflow
- Setup: `uv venv && uv sync`; run the app with `reflex run` (defaults to localhost:3000/api+frontend in a single process).
- Database changes: `reflex db makemigrations "message"` then `reflex db migrate`; inspect generated SQL if the models touch cascading relations.
- Lint/format: `ruff check .` and `ruff format .` (Python 3.13 target, 110-char lines, double quotes enforced via config in `pyproject.toml`).

## Pitfalls & Focus Areas
- Ignore `temp/oldfiles/` and `models/package.py` unless explicitly reviving legacy code—they reflect an abandoned architecture.
- Any new page must be wrapped with `@template(...)` to inherit global metadata, theme, and sidebar; otherwise layout/theming regress.
- When enhancing fetching, remember to surface status through `State.fetch_message` so users see which repo/dist is being processed.
- Upcoming roadmap noted in code comments: fetching/parsing `Packages.gz`, package search, and downloadable `.deb` artifacts—align new contributions with those goals.
````
