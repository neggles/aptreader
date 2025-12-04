import datetime
import logging

from dateutil.parser import parse as parse_date

logger = logging.getLogger(__name__)


def try_parse_date(date_str: str | None) -> datetime.datetime | None:
    """Try to parse a date string into a timestamp.

    Args:
        date_str: The date string to parse (e.g., from HTTP Last-Modified header)

    Returns:
        The parsed timestamp, or None if parsing failed or date_str is None
    """

    try:
        return parse_date(date_str) if date_str else None
    except Exception as e:
        logger.debug(f"Failed to parse date '{date_str}': {e}")
        return None
