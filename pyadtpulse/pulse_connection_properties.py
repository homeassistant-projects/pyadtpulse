"""Pulse connection info."""

from re import search, fullmatch
from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlsplit
from collections.abc import Sequence

from yarl import URL
from aiohttp import CookieJar, ClientSession
from typeguard import typechecked

from .const import (
    API_PREFIX,
    API_HOST_CA,
    DEFAULT_API_HOST,
    ADT_DEFAULT_HTTP_USER_AGENT,
    ADT_DEFAULT_SEC_FETCH_HEADERS,
    ADT_DEFAULT_HTTP_ACCEPT_HEADERS,
)


class PulseConnectionProperties:
    """Pulse connection info."""

    __slots__ = (
        "_api_host",
        "_api_version",
        "_detailed_debug_logging",
        "_session",
        "_user_agent",
    )

    @staticmethod
    @typechecked
    def check_service_host(service_host: str) -> None:
        """Check if service host is valid."""
        if service_host is None or service_host == "":
            raise ValueError("Service host is mandatory")
        if service_host not in (DEFAULT_API_HOST, API_HOST_CA):
            raise ValueError(
                f"Service host must be one of {DEFAULT_API_HOST} or {API_HOST_CA}"
            )

    @staticmethod
    def get_api_version(response_path: str) -> str | None:
        """
        Regex used to exctract the API version.

        Use for testing.
        """
        version: str | None = None
        if not response_path:
            return None
        m = search(f"{API_PREFIX}(.+)/[a-z]*/", response_path)
        if m is not None:
            version = m.group(1)
        return version

    @staticmethod
    def split_versioned_url(url: str) -> tuple[str | None, str]:
        """
        Split a Pulse URL into its API version and the URI after the version.

        "https://portal.adtpulse.com/myhome/31.0.0-39/access/signin.jsp?e=ns"
        gives ("31.0.0-39", "/access/signin.jsp?e=ns"). A URL outside
        /myhome/<version>/ gives (None, path and query).
        """
        parsed = urlsplit(url)
        query = f"?{parsed.query}" if parsed.query else ""
        m = fullmatch(f"{API_PREFIX}([^/]+)(/.*)", parsed.path)
        if m is None:
            return None, parsed.path + query
        return m.group(1), m.group(2) + query

    def __init__(
        self,
        host: str,
        user_agent=ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"],
        detailed_debug_logging=False,
    ) -> None:
        """Initialize Pulse connection information."""
        self.detailed_debug_logging = detailed_debug_logging
        self._session: ClientSession | None = None
        self.service_host = host
        self._api_version = ""
        self._user_agent = user_agent

    def _set_headers(self) -> None:
        if self._session is not None:
            self._session.headers.update(ADT_DEFAULT_HTTP_ACCEPT_HEADERS)
            self._session.headers.update(ADT_DEFAULT_SEC_FETCH_HEADERS)
            self._session.headers.update({"User-Agent": self._user_agent})

    @property
    def service_host(self) -> str:
        """Get the service host."""
        return self._api_host

    @service_host.setter
    @typechecked
    def service_host(self, host: str):
        """
        Set the service host.

        Raises:
            ValueError if host is not valid.

        """
        self.check_service_host(host)
        self._api_host = host

    @property
    def detailed_debug_logging(self) -> bool:
        """Get the detailed debug logging flag."""
        return self._detailed_debug_logging

    @detailed_debug_logging.setter
    @typechecked
    def detailed_debug_logging(self, value: bool):
        """Set the detailed debug logging flag."""
        self._detailed_debug_logging = value

    @property
    def session(self) -> ClientSession:
        """Get the session."""
        if self._session is None:
            self._session = ClientSession(cookie_jar=PulseCookieJar())
        self._set_headers()
        return self._session

    @property
    def api_version(self) -> str:
        """Get the API version."""
        return self._api_version

    @api_version.setter
    @typechecked
    def api_version(self, version: str):
        """
        Set the API version.

        Raises:
            ValueError: if version is not in the form major.minor.patch-subpatch

        """

        def check_version_string(value: str):
            parts = value.split("-")
            if len(parts) == 2:
                version_parts = parts[0].split(".")
                if not (
                    len(version_parts) == 3
                    and version_parts[0].isdigit()
                    and version_parts[1].isdigit()
                    and version_parts[2].isdigit()
                    and parts[1].isdigit()
                ):
                    raise ValueError(
                        "API version must be in the form major.minor.patch-subpatch"
                    )
                if int(version_parts[0]) >= 26:
                    return
                raise ValueError("API version is numeric but less than 26")
            raise ValueError(
                "API version must be in the form major.minor.patch-subpatch"
            )

        check_version_string(version)
        self._api_version = version

    @typechecked
    def make_url(self, uri: str) -> str:
        """
        Create a URL to service host from a URI.

        Args:
            uri (str): the URI to convert

        Returns:
            str: the converted string

        """
        return f"{self._api_host}{API_PREFIX}{self._api_version}{uri}"

    async def async_clear_session(self):
        """Clear the session."""
        old_session = self._session
        self._session = None
        if old_session:
            await old_session.close()


class PulseCookieJar(CookieJar):
    """
    Cookie jar that lets the signed-in Pulse session cookie win.

    At sign-in Pulse sets JSESSIONID on /myhome for the signed-in session, and
    keeps any JSESSIONID already set on /myhome/<version>. A browser sends both
    and the server uses the valid one, but aiohttp sends only the cookie with the
    longest matching path, the stale one, and Pulse then answers
    PostSigninProcessServ with signout.jsp?e=ns ("not signed in"). So when a
    response sets a session cookie on /myhome, drop the ones on longer paths.
    """

    SESSION_COOKIE = "JSESSIONID"
    SESSION_PATH = API_PREFIX.rstrip("/")

    def update_cookies_from_headers(
        self, headers: Sequence[str], response_url: URL
    ) -> None:
        """Store Set-Cookie headers, then drop superseded session cookies."""
        super().update_cookies_from_headers(headers, response_url)
        if any(self._sets_session_cookie(header) for header in headers):
            self.clear(
                lambda morsel: (
                    morsel.key == self.SESSION_COOKIE
                    and morsel["path"] != self.SESSION_PATH
                    and morsel["path"].startswith(f"{self.SESSION_PATH}/")
                )
            )

    @classmethod
    def _sets_session_cookie(cls, header: str) -> bool:
        cookie: SimpleCookie = SimpleCookie()
        try:
            cookie.load(header)
        except CookieError:
            return False
        morsel = cookie.get(cls.SESSION_COOKIE)
        return morsel is not None and morsel["path"].rstrip("/") == cls.SESSION_PATH
