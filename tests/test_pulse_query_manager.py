"""
Test cases for PulseQueryManager class.

This module contains tests that verify the behavior of the PulseQueryManager class,
which handles API version fetching, query retries, and connection error handling.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from aiohttp import client_exceptions, client_reqrep
from aioresponses import aioresponses
from freezegun.api import FrozenDateTimeFactory, StepTickTimeFactory

from pyadtpulse.const import ADT_ORB_URI, DEFAULT_API_HOST
from pyadtpulse.exceptions import (
    PulseClientConnectionError,
    PulseConnectionError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
)
from pyadtpulse.pulse_connection_properties import PulseConnectionProperties
from pyadtpulse.pulse_connection_status import PulseConnectionStatus
from pyadtpulse.pulse_query_manager import MAX_REQUERY_RETRIES, PulseQueryManager
from tests.conftest import MOCKED_API_VERSION

# Constants for backoff testing
INITIAL_BACKOFF = 2
BACKOFF_INTERVAL = 2.0


@pytest.mark.asyncio
async def test_fetch_version(mocked_server_responses: aioresponses):
    """
    Test successful API version fetching.

    Args:
        mocked_server_responses: Fixture providing mocked server responses.

    Verifies that:
        - API version can be fetched successfully
        - Version is correctly stored in connection properties

    """
    s = PulseConnectionStatus()
    cp = PulseConnectionProperties(DEFAULT_API_HOST)
    p = PulseQueryManager(s, cp)
    await p.async_fetch_version()
    assert cp.api_version == MOCKED_API_VERSION


@pytest.mark.asyncio
async def test_fetch_version_fail(mock_server_down: aioresponses):
    """
    Test behavior when API version fetch fails.

    Args:
        mock_server_down: Fixture simulating a server being unreachable.

    Verifies that:
        - Appropriate exception is raised when server is down
        - Backoff is properly incremented
        - Subsequent queries also fail with proper backoff behavior

    """
    s = PulseConnectionStatus()
    cp = PulseConnectionProperties(DEFAULT_API_HOST)
    p = PulseQueryManager(s, cp)
    with pytest.raises(PulseServerConnectionError):
        await p.async_fetch_version()
    assert s.get_backoff().backoff_count == 1
    with pytest.raises(PulseServerConnectionError):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)
    assert s.get_backoff().backoff_count == INITIAL_BACKOFF
    assert s.get_backoff().get_current_backoff_interval() == BACKOFF_INTERVAL


@pytest.mark.asyncio
async def test_fetch_version_eventually_succeeds(
    mock_server_temporarily_down: aioresponses,
):
    """
    Test recovery after temporary version fetch failures.

    Args:
        mock_server_temporarily_down: Fixture simulating a temporarily
            unavailable server.

    Verifies that:
        - Initial failures are handled with proper backoff
        - Eventual success resets backoff count
        - System recovers properly after temporary outage

    """
    s = PulseConnectionStatus()
    cp = PulseConnectionProperties(DEFAULT_API_HOST)
    p = PulseQueryManager(s, cp)
    with pytest.raises(PulseServerConnectionError):
        await p.async_fetch_version()
    assert s.get_backoff().backoff_count == 1
    with pytest.raises(PulseServerConnectionError):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)
    assert s.get_backoff().backoff_count == INITIAL_BACKOFF
    assert s.get_backoff().get_current_backoff_interval() == BACKOFF_INTERVAL
    await p.async_fetch_version()
    assert s.get_backoff().backoff_count == 0


# @pytest.mark.asyncio
# async def test_query_orb(
#     mocked_server_responses: aioresponses,
#     read_file: Callable[..., str],
#     mock_sleep: Any,
#     get_mocked_connection_properties: PulseConnectionProperties,
# ):
#     """Test query orb.

#     We also check that it waits for authenticated flag.
#     """

#     async def query_orb_task():
#         return await p.query_orb(logging.DEBUG, "Failed to query orb")

#     s = PulseConnectionStatus()
#     cp = get_mocked_connection_properties
#     p = PulseQueryManager(s, cp)
#     orb_file = read_file("orb.html")
#     mocked_server_responses.get(
#         cp.make_url(ADT_ORB_URI), status=200, content_type="text/html", body=orb_file
#     )
#     task = asyncio.create_task(query_orb_task())
#     await asyncio.sleep(2)
#     assert not task.done()
#     s.authenticated_flag.set()
#     await task
#     assert task.done()
#     result_etree = task.result()
#     assert result_etree is not None
#     assert html.tostring(result_etree) == orb_file
#     assert mock_sleep.call_count == 1  # from the asyncio.sleep call above
#     mocked_server_responses.get(cp.make_url(ADT_ORB_URI), status=404)
#     with pytest.raises(PulseServerConnectionError):
#         result = await query_orb_task()
#     assert mock_sleep.call_count == 1
#     assert s.get_backoff().backoff_count == 1
#     mocked_server_responses.get(
#         cp.make_url(ADT_ORB_URI), status=200, content_type="text/html", body=orb_file
#     )
#     result = await query_orb_task()
#     assert result is not None
#     assert html.tostring(result) == orb_file
#     assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_retry_after(
    mocked_server_responses: aioresponses,
    freeze_time_to_now: FrozenDateTimeFactory | StepTickTimeFactory,
    get_mocked_connection_properties: PulseConnectionProperties,
    mock_sleep: Any,
):
    """
    Test retry-after header handling.

    Args:
        mocked_server_responses: Fixture providing mocked server responses.
        freeze_time_to_now: Fixture for controlling time during tests.
        get_mocked_connection_properties: Fixture providing connection properties.
        mock_sleep: Fixture for mocking sleep calls.

    Verifies that:
        - Retry-After headers are properly parsed and respected
        - Both numeric and date-based Retry-After values work
        - Queries fail until retry period expires
        - Queries succeed after retry period
        - Backoff state is properly maintained during retries

    """
    retry_after_time = 120
    frozen_time = freeze_time_to_now
    now = time.time()

    s = PulseConnectionStatus()
    cp = get_mocked_connection_properties
    p = PulseQueryManager(s, cp)

    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=429,
        headers={"Retry-After": str(retry_after_time)},
    )
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)
    # make sure we can't override the retry
    s.get_backoff().reset_backoff()
    assert s.get_backoff().expiration_time == int(now + float(retry_after_time))
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)
    frozen_time.tick(timedelta(seconds=retry_after_time + 1))
    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=200,
    )
    # this should succeed
    await p.async_query(ADT_ORB_URI, requires_authentication=False)

    now = time.time()
    retry_date = now + float(retry_after_time)
    retry_date_str = datetime.fromtimestamp(retry_date).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    # need to get the new retry after time since it doesn't have fractions of seconds
    new_retry_after = (
        datetime.strptime(retry_date_str, "%a, %d %b %Y %H:%M:%S GMT").timestamp() - now
    )
    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=503,
        headers={"Retry-After": retry_date_str},
    )
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)

    frozen_time.tick(timedelta(seconds=new_retry_after - 1))
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)
    frozen_time.tick(timedelta(seconds=2))
    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=200,
    )
    # should succeed
    await p.async_query(ADT_ORB_URI, requires_authentication=False)
    # unavailable with no retry after
    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=503,
    )
    frozen_time.tick(timedelta(seconds=retry_after_time + 1))
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)
    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=200,
    )
    # should succeed
    frozen_time.tick(timedelta(seconds=1))
    await p.async_query(ADT_ORB_URI, requires_authentication=False)

    # retry after in the past
    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=503,
        headers={"Retry-After": retry_date_str},
    )
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)
    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=200,
    )
    frozen_time.tick(timedelta(seconds=1))
    # should succeed
    await p.async_query(ADT_ORB_URI, requires_authentication=False)


async def run_query_exception_test(
    mocked_server_responses,
    mock_sleep,
    get_mocked_connection_properties,
    aiohttp_exception: client_exceptions.ClientError,
    pulse_exception: type[PulseConnectionError],
):
    """
    Test query behavior with different exceptions.

    Args:
        mocked_server_responses: Fixture providing mocked server responses.
        mock_sleep: Fixture for mocking sleep calls.
        get_mocked_connection_properties: Fixture providing connection properties.
        aiohttp_exception: The aiohttp exception to simulate.
        pulse_exception: The expected PulseConnection exception type.

    Verifies that:
        - Proper exceptions are raised
        - Retry behavior works correctly
        - Backoff intervals increase appropriately
        - Connection status is properly maintained

    """
    s = PulseConnectionStatus()
    cp = get_mocked_connection_properties
    p = PulseQueryManager(s, cp)

    for _ in range(MAX_REQUERY_RETRIES + 1):
        mocked_server_responses.get(
            cp.make_url(ADT_ORB_URI),
            exception=aiohttp_exception,
        )
    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=200,
    )
    with pytest.raises(pulse_exception):
        await p.async_query(
            ADT_ORB_URI,
            requires_authentication=False,
        )

    assert mock_sleep.call_count == MAX_REQUERY_RETRIES - 1
    for i in range(MAX_REQUERY_RETRIES - 1):
        assert mock_sleep.call_args_list[i][0][0] == 1 * 2**i

    assert s.get_backoff().backoff_count == 1

    with pytest.raises(pulse_exception):
        await p.async_query(ADT_ORB_URI, requires_authentication=False)

    # pqm backoff should trigger here
    assert mock_sleep.call_count == MAX_REQUERY_RETRIES
    assert (
        mock_sleep.call_args_list[MAX_REQUERY_RETRIES - 1][0][0]
        == s.get_backoff().initial_backoff_interval
    )

    mocked_server_responses.get(
        cp.make_url(ADT_ORB_URI),
        status=200,
    )
    # this should trigger a sleep
    await p.async_query(ADT_ORB_URI, requires_authentication=False)
    assert mock_sleep.call_count == MAX_REQUERY_RETRIES + 1
    assert (
        mock_sleep.call_args_list[MAX_REQUERY_RETRIES][0][0]
        == s.get_backoff().initial_backoff_interval * 2
    )
    # this shouldn't trigger a sleep
    await p.async_query(ADT_ORB_URI, requires_authentication=False)
    assert mock_sleep.call_count == MAX_REQUERY_RETRIES + 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_exception",
    (
        (client_exceptions.ClientConnectionError, PulseClientConnectionError),
        (client_exceptions.ClientError, PulseClientConnectionError),
        (client_exceptions.ClientOSError, PulseClientConnectionError),
        (client_exceptions.ServerDisconnectedError, PulseServerConnectionError),
        (client_exceptions.ServerTimeoutError, PulseServerConnectionError),
        (client_exceptions.ServerConnectionError, PulseServerConnectionError),
        (asyncio.TimeoutError, PulseServerConnectionError),
    ),
)
async def test_async_query_exceptions(
    mocked_server_responses: aioresponses,
    mock_sleep: Any,
    get_mocked_connection_properties: PulseConnectionProperties,
    test_exception: tuple[type[Exception], type[PulseConnectionError]],
):
    """
    Test handling of various aiohttp client exceptions.

    Args:
        mocked_server_responses: Fixture providing mocked server responses.
        mock_sleep: Fixture for mocking sleep calls.
        get_mocked_connection_properties: Fixture providing connection properties.
        test_exception: Tuple of (aiohttp exception, expected pulse exception).

    Verifies that:
        - Each exception type is properly caught and converted
        - Retry and backoff behavior is correct for each exception type

    """
    await run_query_exception_test(
        mocked_server_responses,
        mock_sleep,
        get_mocked_connection_properties,
        cast(client_exceptions.ClientError, test_exception[0]()),
        test_exception[1],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_exception",
    (
        (ConnectionRefusedError, PulseServerConnectionError),
        (ConnectionResetError, PulseServerConnectionError),
        # (asyncio.TimeoutError, PulseClientConnectionError),
        # (BrokenPipeError, PulseClientConnectionError),
    ),
)
async def test_async_query_connector_errors(
    mocked_server_responses: aioresponses,
    mock_sleep: Any,
    get_mocked_connection_properties: PulseConnectionProperties,
    test_exception: tuple[type[OSError], type[PulseConnectionError]],
):
    """
    Test handling of various connection errors.

    Args:
        mocked_server_responses: Fixture providing mocked server responses.
        mock_sleep: Fixture for mocking sleep calls.
        get_mocked_connection_properties: Fixture providing connection properties.
        test_exception: Tuple of (OS error, expected pulse exception).


    Verifies that:
        - Various OS-level connection errors are properly handled
        - Errors are converted to appropriate Pulse exceptions
        - Retry and backoff behavior works correctly

    """
    os_error = test_exception[0]()
    connection_key = client_reqrep.ConnectionKey(
        host=DEFAULT_API_HOST,
        port=443,
        is_ssl=True,
        ssl=True,
        proxy=None,
        proxy_auth=None,
        proxy_headers_hash=None,
    )

    aiohttp_exception = client_exceptions.ClientConnectorError(
        connection_key=connection_key, os_error=os_error
    )

    await run_query_exception_test(
        mocked_server_responses,
        mock_sleep,
        get_mocked_connection_properties,
        aiohttp_exception,
        test_exception[1],
    )

    # os_error = test_exception[0]()
    # aiohttp_exception = client_exceptions.ClientConnectorError(
    #     client_reqrep.ConnectionKey(
    #         DEFAULT_API_HOST,
    #         443,
    #         is_ssl=True,
    #         ssl=True,
    #         proxy=None,
    #         proxy_auth=None,
    #         proxy_headers_hash=None,
    #     ),
    #     os_error=cast(OSError, os_error),
    # )
    # await run_query_exception_test(
    #     mocked_server_responses,
    #     mock_sleep,
    #     get_mocked_connection_properties,
    #     aiohttp_exception,
    #     test_exception[1],
    # )
