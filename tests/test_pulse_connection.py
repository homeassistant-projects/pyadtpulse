"""Test cases for PulseConnection class."""

import asyncio
import logging
import datetime
from time import time
from unittest.mock import AsyncMock

import pytest
from yarl import URL

from tests.conftest import LoginType, add_logout, add_signin, add_custom_response
from pyadtpulse.const import ADT_LOGIN_URI, ADT_SUMMARY_URI, DEFAULT_API_HOST
from pyadtpulse.exceptions import (
    PulseMFARequiredError,
    PulseNotLoggedInError,
    PulseAccountLockedError,
    PulseAuthenticationError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
)
from pyadtpulse.pulse_backoff import PulseBackoff
from pyadtpulse.pulse_connection import PulseConnection
from pyadtpulse.pulse_connection_status import PulseConnectionStatus
from pyadtpulse.pulse_connection_properties import PulseConnectionProperties
from pyadtpulse.pulse_authentication_properties import PulseAuthenticationProperties


def setup_pulse_connection() -> PulseConnection:
    """
    Create a PulseConnection instance for testing.

    Returns:
        PulseConnection: A configured PulseConnection instance with test credentials.

    """
    s = PulseConnectionStatus()
    pcp = PulseConnectionProperties(DEFAULT_API_HOST)
    pa = PulseAuthenticationProperties(
        "test@example.com", "testpassword", "testfingerprint"
    )
    return PulseConnection(s, pcp, pa)


# @pytest.mark.asyncio
# async def test_login(mocked_server_responses, read_file, mock_sleep, get_mocked_url):
#     """Test Pulse Connection."""
#     pc = setup_pulse_connection()
#     add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
#     # first call to signin post is successful in conftest.py
#     result = await pc.async_do_login_query()
#     assert result is not None
#     assert html.tostring(result) == read_file("summary.html")
#     assert mock_sleep.call_count == 0
#     assert pc.login_in_progress is False
#     assert pc._login_backoff.backoff_count == 0
#     assert pc._connection_status.authenticated_flag.is_set()
#     # so logout won't fail
#     add_custom_response(
#         mocked_server_responses, read_file, get_mocked_url(ADT_LOGIN_URI)
#     )
#     await pc.async_do_logout_query()
#     assert not pc._connection_status.authenticated_flag.is_set()
#     assert mock_sleep.call_count == 0
#     assert pc._login_backoff.backoff_count == 0


@pytest.mark.asyncio
async def test_login_failure_server_down(mock_server_down):
    """
    Test login behavior when the server is unreachable.

    Args:
        mock_server_down: Fixture that simulates a server being unreachable.

    Verifies that:
        - Appropriate exception is raised when server is down
        - Login state is properly reset after failure
        - No backoff is applied for connection failures

    """
    pc = setup_pulse_connection()
    with pytest.raises(PulseServerConnectionError):
        await pc.async_do_login_query()
    assert pc.login_in_progress is False
    assert pc._login_backoff.backoff_count == 0


# @pytest.mark.asyncio
# async def test_multiple_login(
#     mocked_server_responses, get_mocked_url, read_file, mock_sleep
# ):
#     """Test Pulse Connection."""
#     pc = setup_pulse_connection()
#     add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
#     result = await pc.async_do_login_query()
#     assert result is not None
#     assert html.tostring(result) == read_file("summary.html")
#     assert mock_sleep.call_count == 0
#     assert pc.login_in_progress is False
#     assert pc._login_backoff.backoff_count == 0
#     assert pc._connection_status.authenticated_flag.is_set()
#     add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
#     await pc.async_do_login_query()
#     assert mock_sleep.call_count == 0
#     assert pc.login_in_progress is False
#     assert pc._login_backoff.backoff_count == 0
#     assert pc._connection_status.get_backoff().backoff_count == 0
#     assert pc._connection_status.authenticated_flag.is_set()
#     # this should fail
#     with pytest.raises(PulseServerConnectionError):
#         await pc.async_do_login_query()
#     assert mock_sleep.call_count == MAX_REQUERY_RETRIES - 1
#     assert pc.login_in_progress is False
#     assert pc._login_backoff.backoff_count == 0
#     assert pc._connection_status.get_backoff().backoff_count == 1
#     assert not pc._connection_status.authenticated_flag.is_set()
#     assert not pc.is_connected
#     with pytest.raises(PulseServerConnectionError):
#         await pc.async_do_login_query()
#     assert pc._login_backoff.backoff_count == 0
#     # 2 retries first time, 1 for the connection backoff
#     assert mock_sleep.call_count == MAX_REQUERY_RETRIES
#     assert pc.login_in_progress is False

#     assert pc._connection_status.get_backoff().backoff_count == 2
#     assert not pc._connection_status.authenticated_flag.is_set()
#     assert not pc.is_connected
#     add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
#     await pc.async_do_login_query()
#     # will just to a connection backoff
#     assert mock_sleep.call_count == MAX_REQUERY_RETRIES + 1
#     assert pc.login_in_progress is False
#     assert pc._login_backoff.backoff_count == 0
#     assert pc._connection_status.authenticated_flag.is_set()

#     add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
#     await pc.async_do_login_query()
#     # shouldn't sleep at all
#     assert mock_sleep.call_count == MAX_REQUERY_RETRIES + 1
#     assert pc.login_in_progress is False
#     assert pc._login_backoff.backoff_count == 0
#     assert pc._connection_status.authenticated_flag.is_set()


@pytest.mark.asyncio
async def test_account_lockout(
    mocked_server_responses, mock_sleep, get_mocked_url, read_file, freeze_time_to_now
):
    """
    Test account lockout behavior and recovery.

    Args:
        mocked_server_responses: Fixture for mocked server responses
        mock_sleep: Fixture for mocking sleep calls
        get_mocked_url: Fixture for getting mocked URLs
        read_file: Fixture for reading test data files
        freeze_time_to_now: Fixture for controlling time during tests

    Verifies that:
        - Account lockout is properly detected and handled
        - Lockout expiration works correctly
        - Connection status is properly maintained during lockout
        - No backoff is applied during account lockouts

    """
    pc = setup_pulse_connection()
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    await pc.async_do_login_query()
    assert mock_sleep.call_count == 0
    assert pc.login_in_progress is False
    assert pc._login_backoff.backoff_count == 0
    assert pc.is_connected
    assert pc._connection_status.authenticated_flag.is_set()
    add_signin(LoginType.LOCKED, mocked_server_responses, get_mocked_url, read_file)
    with pytest.raises(PulseAccountLockedError):
        await pc.async_do_login_query()
    # won't sleep yet
    assert not pc.is_connected
    assert not pc._connection_status.authenticated_flag.is_set()
    # don't set backoff on locked account, just set expiration time on backoff
    assert pc._login_backoff.backoff_count == 0
    assert mock_sleep.call_count == 0
    freeze_time_to_now.tick(delta=datetime.timedelta(seconds=(60 * 30) + 1))
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    await pc.async_do_login_query()
    assert mock_sleep.call_count == 0
    assert pc.is_connected
    assert pc._connection_status.authenticated_flag.is_set()
    freeze_time_to_now.tick(delta=datetime.timedelta(seconds=60 * 30 + 1))
    add_signin(LoginType.LOCKED, mocked_server_responses, get_mocked_url, read_file)
    with pytest.raises(PulseAccountLockedError):
        await pc.async_do_login_query()
    assert pc._login_backoff.backoff_count == 0
    assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_invalid_credentials(
    mocked_server_responses, mock_sleep, get_mocked_url, read_file
):
    """
    Test behavior when invalid credentials are provided.

    Args:
        mocked_server_responses: Fixture for mocked server responses
        mock_sleep: Fixture for mocking sleep calls
        get_mocked_url: Fixture for getting mocked URLs
        read_file: Fixture for reading test data files

    Verifies that:
        - Authentication failures are properly detected
        - Appropriate exceptions are raised
        - No backoff is applied for auth failures

    """
    pc = setup_pulse_connection()
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    await pc.async_do_login_query()
    assert mock_sleep.call_count == 0
    assert pc.login_in_progress is False
    assert pc._login_backoff.backoff_count == 0
    add_signin(LoginType.FAIL, mocked_server_responses, get_mocked_url, read_file)
    with pytest.raises(PulseAuthenticationError):
        await pc.async_do_login_query()
    assert pc._login_backoff.backoff_count == 0
    assert mock_sleep.call_count == 0
    add_signin(LoginType.FAIL, mocked_server_responses, get_mocked_url, read_file)

    with pytest.raises(PulseAuthenticationError):
        await pc.async_do_login_query()
    assert pc._login_backoff.backoff_count == 0
    assert mock_sleep.call_count == 0
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    assert pc._login_backoff.backoff_count == 0
    assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_mfa_failure(mocked_server_responses, get_mocked_url, read_file):
    """
    Test behavior when MFA is required but not provided.

    Args:
        mocked_server_responses: Fixture for mocked server responses
        get_mocked_url: Fixture for getting mocked URLs
        read_file: Fixture for reading test data files

    Verifies that:
        - MFA requirement is properly detected
        - Appropriate exceptions are raised
        - No backoff is applied for MFA requirements

    """
    pc = setup_pulse_connection()
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    await pc.async_do_login_query()
    assert pc.login_in_progress is False
    assert pc._login_backoff.backoff_count == 0
    add_signin(LoginType.MFA, mocked_server_responses, get_mocked_url, read_file)
    with pytest.raises(PulseMFARequiredError):
        await pc.async_do_login_query()
    assert pc._login_backoff.backoff_count == 0
    add_signin(LoginType.MFA, mocked_server_responses, get_mocked_url, read_file)
    with pytest.raises(PulseMFARequiredError):
        await pc.async_do_login_query()
    assert pc._login_backoff.backoff_count == 0
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    await pc.async_do_login_query()
    assert pc._login_backoff.backoff_count == 0


@pytest.mark.asyncio
async def test_only_single_login(mocked_server_responses, get_mocked_url, read_file):
    """
    Test that only one login attempt can be in progress at a time.

    Args:
        mocked_server_responses: Fixture for mocked server responses
        get_mocked_url: Fixture for getting mocked URLs
        read_file: Fixture for reading test data files

    Verifies that:
        - Concurrent login attempts are properly handled
        - Only one login process executes at a time
        - Connection status is properly maintained during concurrent attempts

    """

    async def login_task():
        await pc.async_do_login_query()

    pc = setup_pulse_connection()
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    # delay one task for a little bit
    for _i in range(4):
        pc._login_backoff.increment_backoff()
    task1 = asyncio.create_task(login_task())
    task2 = asyncio.create_task(login_task())
    await task2
    assert pc.login_in_progress
    assert not pc.is_connected
    assert not task1.done()
    await task1
    assert not pc.login_in_progress
    assert pc.is_connected


OTHER_API_VERSION = "31.0.0-39"


def _other_version_url(uri: str) -> str:
    return f"{DEFAULT_API_HOST}/myhome/{OTHER_API_VERSION}{uri}"


@pytest.mark.asyncio
async def test_login_redirected_to_other_api_version(
    mocked_server_responses, get_mocked_url, read_file
):
    """
    Test a login that Pulse answers from a different API version.

    Pulse runs more than one API version at once, so a sign-in posted to one
    version can redirect into the summary page of another. That is a
    successful login, and the new version should be used from then on.
    """
    pc = setup_pulse_connection()
    add_custom_response(
        mocked_server_responses,
        read_file,
        get_mocked_url(ADT_LOGIN_URI),
        method="POST",
        status=307,
        headers={"Location": _other_version_url(ADT_SUMMARY_URI)},
    )
    add_custom_response(
        mocked_server_responses,
        read_file,
        _other_version_url(ADT_SUMMARY_URI),
        file_name="summary.html",
    )
    tree = await pc.async_do_login_query()
    assert tree is not None
    assert pc.is_connected
    assert pc._connection_properties.api_version == OTHER_API_VERSION


@pytest.mark.asyncio
async def test_login_error_on_other_api_version(
    mocked_server_responses, get_mocked_url, read_file
):
    """
    Test a failed login that lands on another API version's sign-in page.

    The error on the page should decide the exception, not a generic
    "unexpected response" authentication error.
    """
    pc = setup_pulse_connection()
    signin = _other_version_url(f"{ADT_LOGIN_URI}?e=ns&partner=adt")
    add_custom_response(
        mocked_server_responses,
        read_file,
        get_mocked_url(ADT_LOGIN_URI),
        method="POST",
        status=307,
        headers={"Location": signin},
    )
    add_custom_response(
        mocked_server_responses, read_file, signin, file_name="not_signed_in.html"
    )
    with pytest.raises(PulseNotLoggedInError):
        await pc.async_do_login_query()
    assert not pc.is_connected


@pytest.mark.asyncio
async def test_waiting_query_uses_version_adopted_by_login(
    mocked_server_responses, get_mocked_url, read_file
):
    """A query waiting for login is sent to the version that login landed on."""
    pc = setup_pulse_connection()
    pc._connection_properties.api_version = "27.0.0-140"
    add_custom_response(
        mocked_server_responses,
        read_file,
        _other_version_url(ADT_SUMMARY_URI),
        file_name="summary.html",
    )
    query = asyncio.create_task(pc.async_query(ADT_SUMMARY_URI))
    await asyncio.sleep(0)
    assert not query.done()  # waiting for the authenticated flag
    pc._connection_properties.api_version = OTHER_API_VERSION
    pc._connection_status.authenticated_flag.set()
    status, _, url = await query
    assert status == 200
    assert str(url) == _other_version_url(ADT_SUMMARY_URI)


@pytest.mark.asyncio
async def test_login_error_on_unsupported_api_version(
    mocked_server_responses, get_mocked_url, read_file
):
    """A failed sign-in on a version we would not adopt is still classified."""
    pc = setup_pulse_connection()
    signin = f"{DEFAULT_API_HOST}/myhome/25.0.0-1{ADT_LOGIN_URI}?e=ns&partner=adt"
    add_custom_response(
        mocked_server_responses,
        read_file,
        get_mocked_url(ADT_LOGIN_URI),
        method="POST",
        status=307,
        headers={"Location": signin},
    )
    add_custom_response(
        mocked_server_responses, read_file, signin, file_name="not_signed_in.html"
    )
    with pytest.raises(PulseNotLoggedInError):
        await pc.async_do_login_query()
    assert not pc.login_in_progress


def _login_requests(mocked_server_responses) -> list:
    """Return the sign-in POSTs the mocked server received."""
    return [
        key
        for key in mocked_server_responses.requests
        if key[0] == "POST" and str(key[1]).endswith(ADT_LOGIN_URI)
    ]


def _signin_page(message: str) -> str:
    return f'<html><body><div id="warnMsgContents">{message}</div></body></html>'


@pytest.mark.asyncio
async def test_login_in_progress_cleared_on_value_error(mocker):
    """A ValueError from setting up the query doesn't leave a login running."""
    pc = setup_pulse_connection()
    # no API version and none can be fetched: async_query raises ValueError
    mocker.patch.object(PulseConnection, "async_fetch_version", AsyncMock())
    with pytest.raises(ValueError):
        await pc.async_do_login_query()
    assert pc.login_in_progress is False


@pytest.mark.asyncio
async def test_login_in_progress_cleared_on_empty_response(
    mocked_server_responses, get_mocked_url, read_file
):
    """An empty HTTP 200 sign-in answer is a server error, not a stuck login."""
    pc = setup_pulse_connection()
    add_custom_response(
        mocked_server_responses,
        read_file,
        get_mocked_url(ADT_LOGIN_URI),
        method="POST",
        status=307,
        headers={"Location": _other_version_url(ADT_SUMMARY_URI)},
    )
    # empty body: lxml raises ParserError
    add_custom_response(
        mocked_server_responses, read_file, _other_version_url(ADT_SUMMARY_URI)
    )
    with pytest.raises(PulseServerConnectionError):
        await pc.async_do_login_query()
    assert pc.login_in_progress is False


@pytest.mark.asyncio
async def test_login_in_progress_cleared_on_cancel(mocker):
    """Cancelling a login while it waits clears the in-progress flag."""
    pc = setup_pulse_connection()
    never = asyncio.Event()
    mocker.patch.object(PulseBackoff, "wait_for_backoff", side_effect=never.wait)
    task = asyncio.create_task(pc.async_do_login_query())
    for _ in range(5):
        await asyncio.sleep(0)
    assert pc.login_in_progress
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert pc.login_in_progress is False


@pytest.mark.asyncio
async def test_concurrent_login_does_not_close_first_session(mocker):
    """A login started while another one is resetting the session returns."""
    pc = setup_pulse_connection()
    release = asyncio.Event()
    entered = asyncio.Event()

    async def slow_clear_session() -> None:
        entered.set()
        await release.wait()

    clear = mocker.patch.object(
        PulseConnectionProperties, "clear_session", side_effect=slow_clear_session
    )
    mocker.patch.object(
        PulseBackoff, "wait_for_backoff", side_effect=asyncio.Event().wait
    )
    first = asyncio.create_task(pc.async_do_login_query())
    await entered.wait()
    # the first login is suspended inside quick_logout
    # before the fix it also reset the session, waiting here forever
    assert await asyncio.wait_for(pc.async_do_login_query(), timeout=1) is None
    assert clear.call_count == 1
    first.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert pc.login_in_progress is False


@pytest.mark.asyncio
async def test_check_login_errors_leaves_login_in_progress(get_mocked_url, read_file):
    """Classifying a response must not clear another caller's login flag."""
    pc = setup_pulse_connection()
    pc.login_in_progress = True
    with pytest.raises(PulseNotLoggedInError):
        pc.check_login_errors(
            (200, read_file("not_signed_in.html"), URL(get_mocked_url(ADT_LOGIN_URI)))
        )
    assert pc.login_in_progress is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "seconds"),
    [
        ("Try again in 30 minutes.", 30 * 60),
        ("Try again in 1 minute.", 60),
        ("Try again in 1 hour.", 3600),
        ("Try again in 2 hours.", 7200),
        ("Try again in 45 seconds.", 45),
        ("Sign In unsuccessful. Locked. Try again in 5 Minutes.", 300),
    ],
)
async def test_account_lockout_time_units(
    get_mocked_url, freeze_time_to_now, message, seconds
):
    """The lockout time on the sign-in page is read in its own unit."""
    pc = setup_pulse_connection()
    with pytest.raises(PulseAccountLockedError) as exc:
        pc.check_login_errors(
            (200, _signin_page(message), URL(get_mocked_url(ADT_LOGIN_URI)))
        )
    assert exc.value.retry_time - time() == pytest.approx(seconds, abs=1)


@pytest.mark.asyncio
async def test_sign_in_unsuccessful_is_recognized(get_mocked_url, read_file, caplog):
    """The portal's "Sign In unsuccessful." raises without the generic fallback."""
    pc = setup_pulse_connection()
    with caplog.at_level(logging.ERROR), pytest.raises(PulseAuthenticationError):
        pc.check_login_errors(
            (200, read_file("signin_fail.html"), URL(get_mocked_url(ADT_LOGIN_URI)))
        )
    assert "unexpected response" not in caplog.text


@pytest.mark.asyncio
async def test_login_refused_during_login_backoff(
    mocked_server_responses, get_mocked_url, read_file
):
    """A login while the account lockout lasts raises without a request."""
    pc = setup_pulse_connection()
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    pc._login_backoff.set_absolute_backoff_time(time() + 600)
    with pytest.raises(PulseAccountLockedError):
        await pc.async_do_login_query()
    assert not _login_requests(mocked_server_responses)
    assert pc.login_in_progress is False


@pytest.mark.asyncio
async def test_login_refused_during_retry_after(
    mocked_server_responses, get_mocked_url, read_file
):
    """A login while a Retry-After is active raises without a request."""
    pc = setup_pulse_connection()
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    pc._connection_status.retry_after = time() + 600
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await pc.async_do_login_query()
    assert not _login_requests(mocked_server_responses)
    assert pc.login_in_progress is False


@pytest.mark.asyncio
async def test_logout_closes_session(
    mocked_server_responses, get_mocked_url, read_file
):
    """Logging out closes the aiohttp session."""
    pc = setup_pulse_connection()
    add_signin(LoginType.SUCCESS, mocked_server_responses, get_mocked_url, read_file)
    await pc.async_do_login_query()
    session = pc._connection_properties.session
    add_logout(mocked_server_responses, get_mocked_url, read_file)
    await pc.async_do_logout_query()
    assert session.closed
    assert not pc.is_connected


@pytest.mark.asyncio
async def test_logout_closes_session_when_query_fails(mock_server_down, mock_sleep):
    """The session is closed even if Pulse can't be reached to log out."""
    pc = setup_pulse_connection()
    pc._connection_properties.api_version = OTHER_API_VERSION
    session = pc._connection_properties.session
    await pc.async_do_logout_query()
    assert session.closed
