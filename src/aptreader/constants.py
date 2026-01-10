from os import getenv
from pathlib import Path

try:
    import aiosqlite  # noqa: F401

    aiosqlite_available = True
except ImportError:
    aiosqlite_available = False

# ensure data dir exists
# this will run every time constants.py is imported but that's acceptable
DATA_DIR = Path(getenv("APTREADER_DATA_DIR", "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# repository metadata cache directory
REPOS_DIR = DATA_DIR / "repos"
REPOS_DIR.mkdir(parents=True, exist_ok=True)

if getenv("REFLEX_DB_URI"):
    # we have a database url from the environment, use that
    DB_URL = getenv("REFLEX_DB_URI")
    ASYNC_DB_URL = DB_URL
else:
    # use sqlite
    if DATA_DIR.is_relative_to(Path.cwd()):
        DB_URL = f"sqlite:///{DATA_DIR.relative_to(Path.cwd()) / 'aptreader.db'}"
    else:
        DB_URL = f"sqlite:///{DATA_DIR / 'aptreader.db'}"

    if aiosqlite_available and DB_URL.startswith("sqlite:///"):
        ASYNC_DB_URL = DB_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    else:
        ASYNC_DB_URL = None


# Page routes to always put in the same order at the start/top of the nav/sidebars
ORDERED_PAGE_ROUTES = [
    "/",
    "/repository",
    "/packages",
    "/settings",
]
