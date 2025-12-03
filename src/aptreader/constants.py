from os import getenv
from pathlib import Path

# ensure data dir exists
# this will run every time constants.py is imported but that's acceptable
DATA_DIR = Path(getenv("APTREADER_DATA_DIR", "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# set database url
if DATA_DIR.is_relative_to(Path.cwd()):
    DB_URL = f"sqlite:///{DATA_DIR.relative_to(Path.cwd()) / 'aptreader.db'}"
else:
    DB_URL = f"sqlite:///{DATA_DIR / 'aptreader.db'}"

# Page routes to always put in the same order at the start/top of the nav/sidebars
ORDERED_PAGE_ROUTES = [
    "/",
    "/repository",
    "/packages",
    "/settings",
]
