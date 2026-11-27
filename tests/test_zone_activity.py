"""Zone last activity times on Pulse portals whose orb leaves them out."""

import re
from datetime import datetime
from unittest.mock import AsyncMock
from collections.abc import Callable

import pytest
from lxml import html
from freezegun import freeze_time
from aioresponses import aioresponses

from pyadtpulse.const import ADT_HISTORY_URI
from pyadtpulse.pulse_connection import PulseConnection
from pyadtpulse.pyadtpulse_async import PyADTPulseAsync

NOW = "2026-11-25 22:00:00"


def without_last_event(page: str) -> str:
    """
    Strip the zone rows' last event times, as Pulse 30 and later do.

    Older portals put "Last Event: <time>" in each row's aria-label and in the
    title of its devStatIcon span. Pulse 30.0.0-61 sends neither.
    """
    page = re.sub(r'(<span class="devStatIcon") title="Last Event:[^"]*"', r"\1", page)
    return re.sub(r'aria-label="Last Event:.*?(?:AM|PM) ', 'aria-label="', page)


def history_url(get_mocked_url: Callable[..., str]) -> re.Pattern:
    """Match the history page with any query string."""
    return re.compile(re.escape(get_mocked_url(ADT_HISTORY_URI)) + r"(\?.*)?$")


def history_time_filters(responses: aioresponses) -> list[str]:
    """Return the timefilter of each history page request, in order."""
    return [
        url.query["timefilter"]
        for (method, url), calls in responses.requests.items()
        for _ in calls
        if method == "GET" and url.path.endswith(ADT_HISTORY_URI)
    ]


def local_ts(when: str) -> int:
    """Return the Unix time of a local date and time, the way the code sees it."""
    # freezegun treats naive datetimes as UTC, so convert under the same freeze
    with freeze_time(NOW):
        return int(datetime.fromisoformat(when).timestamp())


async def login(read_file: Callable[..., str], mocker) -> PyADTPulseAsync:
    """Log in, with Pulse answering the sign-in with a portal 30 summary page."""
    p = PyADTPulseAsync("testuser@example.com", "testpassword", "testfingerprint")

    async def login_query() -> html.HtmlElement:
        p._pulse_connection._login_succeeded()
        return html.fromstring(without_last_event(read_file("summary.html")))

    mocker.patch.object(
        PulseConnection, "async_do_login_query", new=AsyncMock(side_effect=login_query)
    )
    await p.async_login()
    return p


async def stop(p: PyADTPulseAsync) -> None:
    """Stop the keepalive task and close the session, without a logout request."""
    await p._cancel_task(p._timeout_task)
    await p._pulse_connection.async_quick_logout()


@pytest.mark.asyncio
async def test_login_reads_last_activity_from_history(
    mocked_server_responses: aioresponses,
    get_mocked_url: Callable[..., str],
    read_file: Callable[..., str],
    mocker,
):
    """Without times in the orb, login reads each zone's newest history event."""
    mocked_server_responses.get(
        history_url(get_mocked_url), body=read_file("history.html")
    )
    with freeze_time(NOW):
        p = await login(read_file, mocker)
    zones = p.site.zones_as_dict
    try:
        assert zones[11].last_activity_timestamp == local_ts("2026-11-25 19:25")
        assert zones[15].last_activity_timestamp == local_ts("2026-11-25 14:43")
        assert zones[9].last_activity_timestamp == local_ts("2026-11-24 23:16")
        assert zones[10].last_activity_timestamp == local_ts("2026-11-24 23:12")
        assert zones[14].last_activity_timestamp == local_ts("2026-11-20 16:53")
        # no event in the history page: the time stays unknown, not "now"
        assert zones[18].last_activity_timestamp == 0
        # login reads a week of history (the longest period offered), once
        assert history_time_filters(mocked_server_responses) == ["168"]
    finally:
        await stop(p)


@pytest.mark.asyncio
async def test_zone_change_reads_last_hour_of_history(
    mocked_server_responses: aioresponses,
    get_mocked_url: Callable[..., str],
    read_file: Callable[..., str],
    mocker,
):
    """A zone that changes gets its time from the past hour of history."""
    history = read_file("history.html")
    mocked_server_responses.get(history_url(get_mocked_url), body=history)
    with freeze_time(NOW):
        p = await login(read_file, mocker)
    try:
        newer = history.replace(
            'Today 7:25 PM</span></th><td valign="middle"><a href="javascript:'
            "historyLinkNavigation('UGF0aW8gRG9vcg==', 'device');\" title=\"Access "
            'device history"><strong>Patio Door</strong></a> (Zone 11) set to '
            "<em>Closed</em>",
            'Today 9:58 PM</span></th><td valign="middle"><a href="javascript:'
            "historyLinkNavigation('UGF0aW8gRG9vcg==', 'device');\" title=\"Access "
            'device history"><strong>Patio Door</strong></a> (Zone 11) set to '
            "<em>Open</em>",
        )
        assert newer != history
        mocked_server_responses.get(
            re.compile(re.escape(get_mocked_url("/ajax/orb.jsp")) + r"(\?.*)?$"),
            body=without_last_event(read_file("orb_patio_opened.html")),
        )
        mocked_server_responses.get(history_url(get_mocked_url), body=newer)
        foyer = p.site.zones_as_dict[15].last_activity_timestamp
        with freeze_time(NOW):
            assert await p.async_update()
        assert p.site.zones_as_dict[11].state == "Open"
        assert p.site.zones_as_dict[11].last_activity_timestamp == local_ts(
            "2026-11-25 21:58"
        )
        # zones that didn't change keep the time they had
        assert p.site.zones_as_dict[15].last_activity_timestamp == foyer
        assert history_time_filters(mocked_server_responses) == ["168", "1"]
    finally:
        await stop(p)


@pytest.mark.asyncio
async def test_unchanged_tripped_zone_skips_history(
    mocked_server_responses: aioresponses,
    get_mocked_url: Callable[..., str],
    read_file: Callable[..., str],
    mocker,
):
    """The orb repeats an open zone on every update; only its change reads history."""
    mocked_server_responses.get(
        history_url(get_mocked_url), body=read_file("history.html"), repeat=True
    )
    with freeze_time(NOW):
        p = await login(read_file, mocker)
    try:
        mocked_server_responses.get(
            re.compile(re.escape(get_mocked_url("/ajax/orb.jsp")) + r"(\?.*)?$"),
            body=without_last_event(read_file("orb_patio_opened.html")),
            repeat=True,
        )
        with freeze_time(NOW):
            assert await p.async_update()
            assert await p.async_update()
        assert p.site.zones_as_dict[11].state == "Open"
        assert history_time_filters(mocked_server_responses) == ["168", "1"]
    finally:
        await stop(p)


@pytest.mark.asyncio
async def test_history_failure_keeps_previous_times(
    mocked_server_responses: aioresponses,
    get_mocked_url: Callable[..., str],
    read_file: Callable[..., str],
    mocker,
    mock_sleep,
):
    """If the history page fails, zones still update and keep their old time."""
    mocked_server_responses.get(history_url(get_mocked_url), status=500, repeat=True)
    p = await login(read_file, mocker)
    try:
        assert p.site.zones_as_dict[11].state == "OK"
        assert all(
            z.last_activity_timestamp == 0 for z in p.site.zones_as_dict.values()
        )
    finally:
        await stop(p)


@pytest.mark.asyncio
async def test_orb_with_last_event_skips_history(
    mocked_server_responses: aioresponses,
    get_mocked_url: Callable[..., str],
    read_file: Callable[..., str],
    mocker,
):
    """Portals that still send the time in the orb need no history request."""
    p = PyADTPulseAsync("testuser@example.com", "testpassword", "testfingerprint")

    async def login_query() -> html.HtmlElement:
        p._pulse_connection._login_succeeded()
        return html.fromstring(read_file("summary.html"))

    mocker.patch.object(
        PulseConnection, "async_do_login_query", new=AsyncMock(side_effect=login_query)
    )
    with freeze_time(NOW):
        await p.async_login()
    try:
        assert p.site.zones_as_dict[11].last_activity_timestamp == local_ts(
            "2026-11-25 19:12"
        )
        assert history_time_filters(mocked_server_responses) == []
    finally:
        await stop(p)
