"""Pulse Query Manager."""

import asyncio
from http import HTTPStatus
from time import time
from asyncio import wait_for
from logging import getLogger
from datetime import timezone
from email.utils import parsedate_to_datetime

from lxml import html
from yarl import URL
from aiohttp import (
    ClientError,
    ClientTimeout,
    ClientResponse,
    ServerTimeoutError,
    ClientResponseError,
    ClientConnectorError,
    ClientConnectionError,
    ServerConnectionError,
    ServerDisconnectedError,
)
from typeguard import typechecked

from .util import make_etree
from .const import (
    ADT_ORB_URI,
    ADT_HTTP_BACKGROUND_URIS,
    ADT_DEFAULT_LOGIN_TIMEOUT,
    ADT_OTHER_HTTP_ACCEPT_HEADERS,
)
from .exceptions import (
    PulseNotLoggedInError,
    PulseClientConnectionError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
)
from .pulse_backoff import PulseBackoff
from .pulse_connection_status import PulseConnectionStatus
from .pulse_connection_properties import PulseConnectionProperties

LOG = getLogger(__name__)

RECOVERABLE_ERRORS = {
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.GATEWAY_TIMEOUT,
}

MAX_REQUERY_RETRIES = 3

DEFAULT_QUERY_TIMEOUT = 10

# request parameters whose values must never be written to the log
REDACTED_PARAMS = frozenset({"usernameForm", "passwordForm", "fingerprint"})
REDACTED_VALUE = "**REDACTED**"


def _redact_params(params: dict[str, str] | None) -> dict[str, str] | None:
    """Return a copy of params with credential values replaced."""
    if params is None:
        return None
    return {
        key: REDACTED_VALUE if key in REDACTED_PARAMS else value
        for key, value in params.items()
    }


class PulseQueryManager:
    """Pulse Query Manager."""

    __slots__ = (
        "_connection_properties",
        "_connection_status",
    )

    @staticmethod
    @typechecked
    def _get_http_status_description(status_code: int) -> str:
        """Get HTTP status description."""
        status = HTTPStatus(status_code)
        return status.description

    @typechecked
    def __init__(
        self,
        connection_status: PulseConnectionStatus,
        connection_properties: PulseConnectionProperties,
    ) -> None:
        """Initialize Pulse Query Manager."""
        self._connection_status = connection_status
        self._connection_properties = connection_properties

    @staticmethod
    @typechecked
    async def _handle_query_response(
        response: ClientResponse | None,
    ) -> tuple[int, str | None, URL | None, str | None]:
        if response is None:
            return 0, None, None, None
        response_text = await response.text()

        return (
            response.status,
            response_text,
            response.url,
            response.headers.get("Retry-After"),
        )

    @typechecked
    def _handle_http_errors(
        self, return_value: tuple[int, str | None, URL | None, str | None]
    ) -> None:
        """
        Handle HTTP errors.

        Args:
            return_value (tuple[int, str | None, URL | None, str | None]):
                The return value from _handle_query_response.

        Raises:
            PulseServerConnectionError: If the server returns an error code.
            PulseServiceTemporarilyUnavailableError: If the server returns a
                HTTP status code of 429 or 503.

        """

        def get_retry_after(retry_after: str) -> int | None:
            """
            Parse the value of the "Retry-After" header.

            Args:
                retry_after (str): The value of the "Retry-After" header

            Returns:
                int | None: The timestamp in seconds to wait before retrying,
                    or None if the header is invalid.

            """
            if retry_after.isnumeric():
                return int(retry_after) + int(time())
            # an HTTP-date is always GMT (RFC 9110 section 5.6.7), never local time
            try:
                retry_date = parsedate_to_datetime(retry_after)
            except (TypeError, ValueError, IndexError):
                return None
            if retry_date.tzinfo is None:
                retry_date = retry_date.replace(tzinfo=timezone.utc)
            return int(retry_date.timestamp())

        if return_value[0] in (
            HTTPStatus.TOO_MANY_REQUESTS,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ):
            retry = None
            if return_value[3]:
                retry = get_retry_after(return_value[3])
            raise PulseServiceTemporarilyUnavailableError(
                self._connection_status.get_backoff(),
                retry,
            )
        raise PulseServerConnectionError(
            f"HTTP error {return_value[0]}: {return_value[1]} connecting to {return_value[2]}",  # noqa: E501
            self._connection_status.get_backoff(),
        )

    @typechecked
    def _handle_network_errors(self, e: Exception) -> None:
        """
        Map a network exception to a Pulse connection exception.

        Server-side failures, including every kind of timeout, raise
        PulseServerConnectionError. Anything else raises
        PulseClientConnectionError.

        Raises:
            PulseServerConnectionError: for server errors and timeouts.
            PulseClientConnectionError: for client-side errors.

        """
        # isinstance, so that aiohttp's subclasses (ConnectionTimeoutError,
        # SocketTimeoutError, ...) are covered too
        # asyncio.TimeoutError is a separate class before Python 3.11
        if isinstance(e, (ServerConnectionError, TimeoutError, asyncio.TimeoutError)):
            raise PulseServerConnectionError(
                str(e), self._connection_status.get_backoff()
            )
        if isinstance(e, ClientConnectorError):
            if isinstance(e.os_error, BrokenPipeError):
                raise PulseClientConnectionError(
                    str(e), self._connection_status.get_backoff()
                )
            raise PulseServerConnectionError(
                str(e), self._connection_status.get_backoff()
            )
        if (
            isinstance(e, ClientConnectionError) and "Connection refused" in str(e)
        ) or "timed out" in str(e):
            raise PulseServerConnectionError(
                str(e), self._connection_status.get_backoff()
            )
        raise PulseClientConnectionError(str(e), self._connection_status.get_backoff())

    @typechecked
    async def async_query(  # noqa: PLR0912, PLR0915
        self,
        uri: str,
        method: str = "GET",
        extra_params: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: int | float = DEFAULT_QUERY_TIMEOUT,
        requires_authentication: bool = True,
    ) -> tuple[int, str | None, URL | None]:
        """
        Query ADT Pulse async.

        Args:
            uri (str): URI to query
            method (str, optional): method to use. Defaults to "GET".
            extra_params (Optional[Dict], optional): query/body parameters.
                                                    Defaults to None.
            extra_headers (Optional[Dict], optional): extra HTTP headers.
                                                    Defaults to None.
            timeout (int | float, optional): total timeout in seconds for each
                                                    attempt, including reading the
                                                    response body. Defaults to 10.
            requires_authentication (bool, optional): True if authentication is
                                                    required to perform query.
                                                    Defaults to True.
                                                    If true and authenticated flag not
                                                    set, will wait for flag to be set.

        Returns:
            tuple with integer return code, optional response text, and optional URL of
            response

        Raises:
            PulseClientConnectionError: If the client cannot connect
            PulseServerConnectionError: If there is a server error
            PulseServiceTemporarilyUnavailableError: If the response code is 429 or 503
            PulseNotLoggedInError: if not logged in and task is waiting for longer than
                ADT_DEFAULT_LOGIN_TIMEOUT seconds

        """

        async def setup_query():
            if method not in ("GET", "POST"):
                raise ValueError("method must be GET or POST")
            await self._connection_status.get_backoff().async_wait_for_backoff()
            if not self._connection_properties.api_version:
                await self.async_fetch_version()
                if not self._connection_properties.api_version:
                    raise ValueError("Could not determine API version for connection")

        retry_after = self._connection_status.retry_after
        now = time()
        if retry_after > now:
            raise PulseServiceTemporarilyUnavailableError(
                self._connection_status.get_backoff(), retry_after
            )
        await setup_query()
        url = self._connection_properties.make_url(uri)
        # copy, so the caller's dict is never changed
        headers = dict(extra_headers) if extra_headers is not None else {}
        if uri in ADT_HTTP_BACKGROUND_URIS:
            headers.setdefault("Accept", ADT_OTHER_HTTP_ACCEPT_HEADERS["Accept"])
        if self._connection_properties.detailed_debug_logging:
            LOG.debug(
                "Attempting %s %s params=%s timeout=%s",
                method,
                url,
                _redact_params(extra_params),
                timeout,
            )
        retry = 0
        return_value: tuple[int, str | None, URL | None, str | None] = (
            HTTPStatus.OK.value,
            None,
            None,
            None,
        )
        query_backoff = PulseBackoff(
            f"Query:{method} {uri}",
            self._connection_status.get_backoff().initial_backoff_interval,
            threshold=0,
            detailed_debug_logging=self._connection_properties.detailed_debug_logging,
        )
        max_retries = (
            MAX_REQUERY_RETRIES
            if not self._connection_status.get_backoff().will_backoff()
            else 1
        )
        while retry < max_retries:
            try:
                await query_backoff.async_wait_for_backoff()
                retry += 1
                if (
                    requires_authentication
                    and not self._connection_status.authenticated_flag.is_set()
                ):
                    if self._connection_properties.detailed_debug_logging:
                        LOG.debug(
                            "%s for %s waiting for authenticated flag to be set",
                            method,
                            uri,
                        )
                    # wait for authenticated flag to be set
                    # use a timeout to prevent waiting forever
                    try:
                        await wait_for(
                            self._connection_status.authenticated_flag.wait(),
                            ADT_DEFAULT_LOGIN_TIMEOUT,
                        )
                    # asyncio.TimeoutError is a separate class before Python 3.11
                    except (TimeoutError, asyncio.TimeoutError) as ex:
                        LOG.warning(
                            "%s for %s timed out waiting for authenticated flag to be set",  # noqa: E501
                            method,
                            uri,
                        )
                        raise PulseNotLoggedInError() from ex
                # build it now: a login while we waited may have changed version
                url = self._connection_properties.make_url(uri)
                async with self._connection_properties.session.request(
                    method,
                    url,
                    headers=headers,
                    params=extra_params if method == "GET" else None,
                    data=extra_params if method == "POST" else None,
                    timeout=ClientTimeout(total=float(timeout)),
                ) as response:
                    return_value = await self._handle_query_response(response)
                    if return_value[0] in RECOVERABLE_ERRORS:
                        LOG.debug(
                            "query returned recoverable error code %s: %s,"
                            "retrying (count = %d)",
                            return_value[0],
                            self._get_http_status_description(return_value[0]),
                            retry,
                        )
                        if retry < max_retries:
                            query_backoff.increment_backoff()
                            continue
                        LOG.debug("Exceeded max retries of %d, giving up", max_retries)
                    # out of retries for a recoverable error, or any other error
                    # status: raises ClientResponseError, handled below
                    response.raise_for_status()
                    break

            except ClientResponseError:
                self._handle_http_errors(return_value)
            except UnicodeDecodeError as ex:
                raise PulseServerConnectionError(
                    f"Could not decode response from {url}: {ex}",
                    self._connection_status.get_backoff(),
                ) from ex
            except (
                ClientConnectorError,
                ServerTimeoutError,
                ClientError,
                ServerConnectionError,
                ServerDisconnectedError,
            ) as ex:
                LOG.debug(
                    "Error %s occurred making %s request to %s",
                    ex.args,
                    method,
                    url,
                    exc_info=True,
                )
                if retry == max_retries:
                    self._handle_network_errors(ex)
                query_backoff.increment_backoff()
                continue
            except (TimeoutError, asyncio.TimeoutError) as ex:
                if retry == max_retries:
                    LOG.debug("Exceeded max retries of %d, giving up", max_retries)
                    raise PulseServerConnectionError(
                        "Timeout error",
                        self._connection_status.get_backoff(),
                    ) from ex
                query_backoff.increment_backoff()
                continue
        # success
        self._connection_status.get_backoff().reset_backoff()
        return (return_value[0], return_value[1], return_value[2])

    async def async_query_orb(
        self, level: int, error_message: str
    ) -> html.HtmlElement | None:
        """
        Query ADT Pulse ORB.

        Args:
            level (int): error level to log on failure
            error_message (str): error message to use on failure

        Returns:
            Optional[html.HtmlElement]: the parsed response tree

        Raises:
            PulseClientConnectionError: If the client cannot connect
            PulseServerConnectionError: If there is a server error
            PulseServiceTemporarilyUnavailableError: If the server returns a
                Retry-After header

        """
        code, response, url = await self.async_query(
            ADT_ORB_URI,
            extra_headers={"Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty"},
        )

        return make_etree(code, response, url, level, error_message)

    async def async_fetch_version(self) -> None:
        """
        Fetch ADT Pulse version.

        Exceptions are passed through to the caller since if this fails, there is
        probably some underlying connection issue.
        """
        response_values: tuple[int, str | None, URL | None, str | None] = (
            HTTPStatus.OK.value,
            None,
            None,
            None,
        )
        if self._connection_properties.api_version:
            return

        signin_url = self._connection_properties.service_host
        try:
            async with self._connection_properties.session.get(
                signin_url,
                timeout=ClientTimeout(total=float(10)),
            ) as response:
                response_values = await self._handle_query_response(response)
                response.raise_for_status()

        except ClientResponseError as ex:
            LOG.error(
                "Error %s occurred determining Pulse API version",
                ex.args,
                exc_info=True,
            )
            self._handle_http_errors(response_values)
        except UnicodeDecodeError as ex:
            raise PulseServerConnectionError(
                f"Could not decode response determining Pulse API version: {ex}",
                self._connection_status.get_backoff(),
            ) from ex
        except (
            ClientConnectorError,
            ServerTimeoutError,
            ClientError,
            ServerConnectionError,
        ) as ex:
            LOG.error(
                "Error %s occurred determining Pulse API version",
                ex.args,
                exc_info=True,
            )
            self._handle_network_errors(ex)
        # asyncio.TimeoutError is a separate class before Python 3.11
        except (TimeoutError, asyncio.TimeoutError) as ex:
            LOG.error(
                "Timeout occurred determining Pulse API version %s",
                ex.args,
                exc_info=True,
            )
            raise PulseServerConnectionError(
                "Timeout occurred determining Pulse API version",
                self._connection_status.get_backoff(),
            ) from ex
        version = self._connection_properties.get_api_version(str(response_values[2]))
        if version is not None:
            self._connection_properties.api_version = version
            LOG.debug(
                "Discovered ADT Pulse version %s at %s",
                self._connection_properties.api_version,
                self._connection_properties.service_host,
            )
            self._connection_status.get_backoff().reset_backoff()
