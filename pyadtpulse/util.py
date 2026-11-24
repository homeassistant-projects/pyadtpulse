"""Utility functions for pyadtpulse."""

import string
import logging
import secrets
from datetime import datetime, timedelta

from lxml import html
from yarl import URL

LOG = logging.getLogger(__name__)


def remove_prefix(text: str, prefix: str) -> str:
    """
    Remove prefix from a string.

    Args:
        text (str): original text
        prefix (str): prefix to remove

    Returns:
        str: modified string

    """
    return text[text.startswith(prefix) and len(prefix) :]


def handle_response(code: int, url: URL | None, level: int, error_message: str) -> bool:
    """
    Handle the response from query().

    Args:
        code: (int): the return code
        url: (Optional[URL]): the URL that was queried
        level: (int): Level to log on error (i.e. INFO, DEBUG)
        error_message: (str): the error message

    Returns:
        bool: True if no error occurred.

    """
    if code >= 400:
        LOG.log(level, "%s: error code = %s from %s", error_message, code, url)
        return False
    return True


def make_etree(
    code: int,
    response_text: str | None,
    url: URL | None,
    level: int,
    error_message: str,
) -> html.HtmlElement | None:
    """
    Make a parsed HTML tree from a Response using lxml.

    Args:
        code: (int): the return code
        response_text: (Optional[str]): the response text
        url: (Optional[URL]): the URL that was queried
        level: (int): the logging level on error
        error_message: (str): the error message

    Returns:
        Optional[html.HtmlElement]: a parsed HTML tree, or None on failure

    """
    if not handle_response(code, url, level, error_message):
        return None
    if response_text is None:
        LOG.log(level, "%s: no response received from %s", error_message, url)
        return None
    return html.fromstring(response_text)


FINGERPRINT_LENGTH = 2292
ALLOWABLE_CHARACTERS = list(string.ascii_letters + string.digits)
FINGERPRINT_RANGE_LEN = len(ALLOWABLE_CHARACTERS)


def generate_random_fingerprint() -> str:
    """
    Generate a random browser fingerprint string.

    Returns:
        str: a fingerprint string

    """
    # The fingerprint identifies a trusted device that can skip MFA, so it
    # comes from a cryptographically secure generator.
    return "".join(
        secrets.choice(ALLOWABLE_CHARACTERS) for _ in range(FINGERPRINT_LENGTH)
    )


def parse_pulse_datetime(datestring: str) -> datetime:
    """
    Parse pulse date strings.

    Args:
        datestring (str): the string to parse

    Raises:
        ValueError: pass through of value error if string
                    cannot be converted

    Returns:
        datetime: time value of given string

    """
    datestring = datestring.replace("\xa0", " ").rstrip()
    split_string = [s for s in datestring.split(" ") if s.strip()]
    if len(split_string) < 3:
        raise ValueError("Invalid datestring")
    t = datetime.today()
    if split_string[0].lstrip() == "Today":
        last_update = t
    elif split_string[0].lstrip() == "Yesterday":
        last_update = t - timedelta(days=1)
    else:
        tempdate = f"{split_string[0]}/{t.year}"
        last_update = datetime.strptime(tempdate, "%m/%d/%Y")
    if last_update > t:
        last_update = last_update.replace(year=t.year - 1)
    update_time = datetime.time(
        datetime.strptime(split_string[1] + split_string[2], "%I:%M%p")
    )
    last_update = datetime.combine(last_update, update_time)
    return last_update
