"""Test cases for PulseConnectionProperties class."""

from asyncio import AbstractEventLoop

import pytest
from yarl import URL
from aiohttp import ClientSession

from pyadtpulse.const import API_HOST_CA, DEFAULT_API_HOST, ADT_DEFAULT_HTTP_USER_AGENT
from pyadtpulse.pulse_connection_properties import (
    PulseCookieJar,
    PulseConnectionProperties,
)


class TestPulseConnectionProperties:
    """Test cases for PulseConnectionProperties class."""

    @pytest.mark.asyncio
    async def test_initialize_with_valid_host(self):
        """Test initializing PulseConnectionProperties with a valid host."""
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False

        # Act
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Assert
        assert connection_properties.service_host == host
        assert connection_properties._user_agent == user_agent
        assert connection_properties._detailed_debug_logging == detailed_debug_logging
        assert connection_properties._debug_locks == debug_locks

    @pytest.mark.asyncio
    async def test_set_service_host_to_default_api_host(self):
        """Test setting the service host to the default API host."""
        # Arrange
        host = DEFAULT_API_HOST
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        connection_properties.service_host = DEFAULT_API_HOST

        # Assert
        assert connection_properties.service_host == DEFAULT_API_HOST

    @pytest.mark.asyncio
    async def test_set_service_host_to_api_host_ca(self):
        """Test setting the service host to the Canadian API host."""
        # Arrange
        host = DEFAULT_API_HOST
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        connection_properties.service_host = API_HOST_CA

        # Assert
        assert connection_properties.service_host == API_HOST_CA

    @pytest.mark.asyncio
    async def test_get_service_host(self):
        """Test retrieving the service host property."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act & Assert
        assert connection_properties.service_host == host

    @pytest.mark.asyncio
    async def test_set_detailed_debug_logging_to_true(self):
        """Test enabling detailed debug logging."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        connection_properties.detailed_debug_logging = True

        # Assert
        assert connection_properties.detailed_debug_logging is True

    @pytest.mark.asyncio
    async def test_set_detailed_debug_logging_to_false(self):
        """Test disabling detailed debug logging."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = True
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        connection_properties.detailed_debug_logging = False

        # Assert
        assert connection_properties.detailed_debug_logging is False

    @pytest.mark.asyncio
    async def test_initialize_with_invalid_host_raises_value_error(self):
        """Test that initializing with an invalid host raises ValueError."""
        # Arrange
        host = ""
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False

        # Act & Assert
        with pytest.raises(ValueError):
            PulseConnectionProperties(
                host, user_agent, detailed_debug_logging, debug_locks
            )

    @pytest.mark.asyncio
    async def test_set_service_host_to_valid_host_does_not_raise_value_error(self):
        """Test that setting a valid service host does not raise ValueError."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act & Assert
        connection_properties.service_host = host

    @pytest.mark.asyncio
    async def test_set_api_version_to_invalid_version_raises_value_error(self):
        """Test that setting an invalid API version raises ValueError."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act & Assert
        with pytest.raises(ValueError):
            connection_properties.api_version = "1.0"

    @pytest.mark.asyncio
    async def test_check_sync_without_setting_event_loop_raises_runtime_error(self):
        """Test that checking sync without setting event loop raises RuntimeError."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act & Assert
        with pytest.raises(RuntimeError):
            connection_properties.check_sync("Sync login was not performed")

    @pytest.mark.asyncio
    async def test_get_detailed_debug_logging_flag(self):
        """Test retrieving the detailed debug logging flag."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = True
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        result = connection_properties.detailed_debug_logging

        # Assert
        assert result == detailed_debug_logging

    @pytest.mark.asyncio
    async def test_set_debug_locks_to_true_with_valid_service_host(self):
        """Test enabling debug locks with a valid service host."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = True

        # Act
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Assert
        assert connection_properties.service_host == host
        assert connection_properties._user_agent == user_agent
        assert connection_properties._detailed_debug_logging == detailed_debug_logging
        assert connection_properties._debug_locks == debug_locks

    @pytest.mark.asyncio
    async def test_get_debug_locks_flag(self):
        """Test retrieving the debug locks flag."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = True

        # Act
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Assert
        assert connection_properties.debug_locks == debug_locks

    @pytest.mark.asyncio
    async def test_set_debug_locks_to_false_with_valid_service_host(self):
        """Test disabling debug locks with a valid service host."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False

        # Act
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Assert
        assert connection_properties.debug_locks == debug_locks

    @pytest.mark.asyncio
    async def test_set_event_loop(self):
        """Test setting the event loop property."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        loop = AbstractEventLoop()

        # Act
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )
        connection_properties.loop = loop

        # Assert
        assert connection_properties.loop == loop

    @pytest.mark.asyncio
    async def test_get_event_loop(self):
        """Test retrieving the event loop property."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        event_loop = connection_properties.loop

        # Assert
        assert event_loop is None

    @pytest.mark.asyncio
    async def test_set_api_version(self):
        """Test setting API version with various valid and invalid versions."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        version = "26.0.0-subpatch"

        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        with pytest.raises(ValueError):
            connection_properties.api_version = version
        version = "26.0.0"
        with pytest.raises(ValueError):
            connection_properties.api_version = version
        version = "25.0.0-22"
        with pytest.raises(ValueError):
            connection_properties.api_version = version
        version = "26.0.0-22"
        connection_properties.api_version = version
        # Assert
        assert connection_properties.api_version == version

    @pytest.mark.asyncio
    async def test_get_api_version(self):
        """Test retrieving API version from response path."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        response_path = "example.com/api/v1"

        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act and Assert
        assert connection_properties.get_api_version(response_path) is None

    @pytest.mark.asyncio
    async def test_get_session_with_valid_host(self):
        """Test creating and retrieving client session with valid host."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        session = connection_properties.session

        # Assert
        assert isinstance(session, ClientSession)
        assert connection_properties._session == session

    @pytest.mark.asyncio
    async def test_check_async_after_setting_event_loop_raises_runtime_error(self):
        """Test that checking async after setting event loop raises RuntimeError."""
        # Arrange
        host = "https://portal.adtpulse.com"
        user_agent = ADT_DEFAULT_HTTP_USER_AGENT["User-Agent"]
        detailed_debug_logging = False
        debug_locks = False
        connection_properties = PulseConnectionProperties(
            host, user_agent, detailed_debug_logging, debug_locks
        )

        # Act
        connection_properties.loop = AbstractEventLoop()

        # Assert
        with pytest.raises(RuntimeError):
            connection_properties.check_async("Async login not performed")


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://portal.adtpulse.com/myhome/31.0.0-39/access/signin.jsp?e=ns&partner=adt",
            ("31.0.0-39", "/access/signin.jsp?e=ns&partner=adt"),
        ),
        (
            "https://portal.adtpulse.com/myhome/30.0.0-61/summary/summary.jsp",
            ("30.0.0-61", "/summary/summary.jsp"),
        ),
        (
            "https://portal.adtpulse.com/myhome/30.0.0-61/mfa/mfaSignIn.jsp?workflow=challenge",
            ("30.0.0-61", "/mfa/mfaSignIn.jsp?workflow=challenge"),
        ),
        ("https://portal.adtpulse.com/", (None, "/")),
    ],
)
def test_split_versioned_url(url, expected):
    """Test splitting a Pulse URL into its API version and the URI after it."""
    assert PulseConnectionProperties.split_versioned_url(url) == expected


# Set-Cookie headers from a real Pulse sign-in (values replaced): the response
# to the sign-in POST keeps the pre-login session cookie on /myhome/<version>
# and adds the signed-in one on /myhome.
SIGNIN_URL = URL("https://portal.adtpulse.com/myhome/30.0.0-61/access/signin.jsp")
PRE_LOGIN_SET_COOKIE = [
    "JSESSIONID=prelogin; path=/myhome/30.0.0-61; HttpOnly; secure; SameSite=Lax"
]
SIGNIN_SET_COOKIE = [
    "JSESSIONID=prelogin; path=/myhome/30.0.0-61; HttpOnly; secure; SameSite=Lax",
    "JSESSIONID=signedin; Path=/myhome; Secure; HttpOnly",
    "ICLocal=en_US; Expires=Sat, 20 Nov 2027 22:56:55 GMT; Path=/",
    "X-token=token; Version=1; Domain=.adtpulse.com; Path=/; Secure; HttpOnly",
]
POST_SIGNIN_URL = URL(
    "https://portal.adtpulse.com/myhome/30.0.0-61/access/PostSigninProcessServ"
)


@pytest.mark.asyncio
async def test_signed_in_session_cookie_wins():
    """After sign-in the signed-in JSESSIONID, not the pre-login one, is sent."""
    jar = PulseCookieJar()
    jar.update_cookies_from_headers(PRE_LOGIN_SET_COOKIE, SIGNIN_URL)
    assert jar.filter_cookies(POST_SIGNIN_URL)["JSESSIONID"].value == "prelogin"
    jar.update_cookies_from_headers(SIGNIN_SET_COOKIE, SIGNIN_URL)
    cookies = jar.filter_cookies(POST_SIGNIN_URL)
    assert cookies["JSESSIONID"].value == "signedin"
    assert cookies["X-token"].value == "token"


@pytest.mark.asyncio
async def test_later_version_session_cookie_is_kept():
    """A session cookie Pulse sets on /myhome/<version> after sign-in is kept."""
    jar = PulseCookieJar()
    jar.update_cookies_from_headers(SIGNIN_SET_COOKIE, SIGNIN_URL)
    jar.update_cookies_from_headers(
        ["JSESSIONID=fresh; path=/myhome/30.0.0-61; HttpOnly; secure"], POST_SIGNIN_URL
    )
    assert jar.filter_cookies(POST_SIGNIN_URL)["JSESSIONID"].value == "fresh"


@pytest.mark.asyncio
async def test_session_uses_pulse_cookie_jar():
    """The connection's session stores cookies in a PulseCookieJar."""
    p = PulseConnectionProperties("https://portal.adtpulse.com")
    assert isinstance(p.session.cookie_jar, PulseCookieJar)
    await p.clear_session()
