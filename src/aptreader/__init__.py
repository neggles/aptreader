import logging

import socketio
from rich.logging import RichHandler

from . import db  # noqa: F401 # ensure DB stuff is initialized

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            tracebacks_suppress=[socketio],
        )
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
