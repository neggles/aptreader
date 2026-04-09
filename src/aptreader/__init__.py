import logging

import socketio
from rich.logging import RichHandler

from . import db  # noqa: F401 # ensure DB stuff is initialized

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(name)s] %(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            show_path=True,
            rich_tracebacks=False,
            tracebacks_suppress=[socketio],
            tracebacks_show_locals=True,
            tracebacks_code_width=120,
        )
    ],
)
logging.getLogger("aptreader").setLevel(logging.DEBUG)
for logger_name in ["httpx", "httpcore", "sqlmodel", "sqlalchemy", "asyncio", "watchfiles"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
