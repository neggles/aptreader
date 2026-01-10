import logging

import socketio
from rich.logging import RichHandler

from . import db  # noqa: F401 # ensure DB stuff is initialized

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s %(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            show_path=True,
            rich_tracebacks=True,
            tracebacks_suppress=[socketio],
            tracebacks_show_locals=True,
            tracebacks_code_width=120,
        )
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
