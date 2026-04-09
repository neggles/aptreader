import asyncio
import inspect
import logging
from datetime import UTC, datetime, timezone
from functools import wraps

from dateutil.parser import parse as parse_date

logger = logging.getLogger(__name__)


def try_parse_date(date_str: str | None, tz: timezone | None = None) -> datetime | None:
    """Try to parse a date string into a datetime.

    Args:
        date_str: The date string to parse (e.g., from HTTP Last-Modified header)

    Returns:
        The parsed datetime, or None if parsing failed or date_str is None
    """

    try:
        if date_str is None:
            return None
        dt = parse_date(date_str)
        if tz:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            else:
                dt = dt.astimezone(tz)
        return dt
    except Exception as e:
        logger.debug(f"Failed to parse date '{date_str}': {e}")
        return None


def long_running_task(func):
    """Decorator to mark a function as a long-running task.

    This hoists the try/catch for asyncio.CancelledError out of the wrapped function,
    which saves a level of indentation and makes the code cleaner.

    Args:
        func: The function to decorate.
    Returns:
        The decorated function.

    """
    is_async_gen = inspect.isasyncgenfunction(func)
    is_coro = inspect.iscoroutinefunction(func)

    if not is_async_gen and not is_coro:
        raise ValueError("long_running_task only supports async functions.")

    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_async_gen:

            async def inner_gen():
                try:
                    async for item in func(*args, **kwargs):
                        yield item
                except asyncio.CancelledError:
                    logger.debug(f"Long-running task {func.__name__} was cancelled.")
                    raise

            return inner_gen()
        elif is_coro:
            try:

                async def inner_coro():
                    return await func(*args, **kwargs)
            except asyncio.CancelledError:
                logger.debug(f"Long-running task {func.__name__} was cancelled.")
                raise

            return inner_coro()
        else:
            raise ValueError("long_running_task decorator can only be applied to async functions.")

    return wrapper


def stringify_size(num: int | float, decimal: bool = False, separator: str = "") -> str:
    """Converts a byte size to a human readable string.

    Args:
        num: The byte size to convert.
        decimal: If True, use decimal units (e.g. 1000 bytes per KB). If False, use binary units
            (e.g. 1024 bytes per KiB).
        separator: A string used to split the value and unit. Defaults to an empty string ('').

    Returns:
        A human readable string representation of the byte size.
    """
    if decimal:
        divisor = 1000
        units = "B", "KB", "MB", "GB", "TB", "PB"
        final_unit = "EB"
    else:
        divisor = 1024
        units = "B", "KiB", "MiB", "GiB", "TiB", "PiB"
        final_unit = "EiB"

    num = float(num)
    for unit in units:
        if abs(num) < divisor:
            if unit == "B":
                return f"{num:0.0f}{separator}{unit}"
            else:
                return f"{num:0.1f}{separator}{unit}"
        num /= divisor

    return f"{num:0.1f}{separator}{final_unit}"


def clean_text(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else value or None


def utcnow():
    """Get the current UTC time."""
    return datetime.now(tz=UTC)
