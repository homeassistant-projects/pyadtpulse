"""Tests for ADTPulseAlarmPanel: parsing, state properties and arm/disarm."""

import re
import logging
from time import time
from collections.abc import Generator

import pytest
from lxml import html
from freezegun import freeze_time
from aioresponses import aioresponses

from pyadtpulse.const import ADT_ARM_DISARM_URI
from pyadtpulse.exceptions import PulseServerConnectionError
from pyadtpulse.alarm_panel import (
    ADT_ALARM_OFF,
    ADT_ALARM_AWAY,
    ADT_ALARM_HOME,
    ADT_ALARM_NIGHT,
    ADT_ALARM_ARMING,
    ADT_ALARM_UNKNOWN,
    ADT_ALARM_DISARMING,
    ADT_ARM_DISARM_TIMEOUT,
    ADTPulseAlarmPanel,
)
from pyadtpulse.pulse_connection import PulseConnection
from pyadtpulse.pulse_connection_status import PulseConnectionStatus
from pyadtpulse.pulse_authentication_properties import PulseAuthenticationProperties

SUMMARY_SAT = "59c7fb63-7432-40b8-9b7c-6a8eeeb83087"
TEST_SAT = "1234abcd-5678"


def status_page(status_text: str) -> html.HtmlElement:
    """Build a minimal summary page with the given alarm status text."""
    return html.fromstring(
        "<html><body>"
        f'<span class="p_boldNormalTextLarge">{status_text}</span>'
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# update_alarm_from_etree
# ---------------------------------------------------------------------------


def test_update_from_summary(read_file):
    """The saved summary page is parsed as disarmed and the sat is extracted."""
    panel = ADTPulseAlarmPanel()
    panel.update_alarm_from_etree(html.fromstring(read_file("summary.html")))
    assert panel.status == ADT_ALARM_OFF
    assert panel.is_disarmed
    assert panel._sat == SUMMARY_SAT


def test_update_from_page_without_status_span(read_file, caplog):
    """A page without the status span (e.g. signed out) marks the state unknown."""
    panel = ADTPulseAlarmPanel(_status=ADT_ALARM_AWAY)
    with caplog.at_level(logging.WARNING):
        panel.update_alarm_from_etree(html.fromstring(read_file("not_signed_in.html")))
    assert panel.status == ADT_ALARM_UNKNOWN
    assert "Failed to find alarm status" in caplog.text


def test_update_from_empty_status_span(caplog):
    """An empty status span marks the state unknown instead of raising."""
    panel = ADTPulseAlarmPanel(_status=ADT_ALARM_AWAY)
    with caplog.at_level(logging.WARNING):
        panel.update_alarm_from_etree(status_page(""))
    assert panel.status == ADT_ALARM_UNKNOWN
    assert "Failed to get alarm status from ''" in caplog.text


def test_update_from_gateway_offline_page(read_file, caplog):
    """'Status Unavailable' marks the state unknown without a warning."""
    panel = ADTPulseAlarmPanel(_status=ADT_ALARM_OFF)
    with caplog.at_level(logging.WARNING):
        panel.update_alarm_from_etree(
            html.fromstring(read_file("summary_gateway_offline.html"))
        )
    assert panel.status == ADT_ALARM_UNKNOWN
    assert "Failed to get alarm status" not in caplog.text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Disarmed. All Quiet.", ADT_ALARM_OFF),
        ("Armed Away. All Quiet.", ADT_ALARM_AWAY),
        ("Armed Stay. 1 Sensor Open.", ADT_ALARM_HOME),
        ("Armed Night. All Quiet.", ADT_ALARM_NIGHT),
    ],
)
def test_update_status_texts(text, expected):
    """Each portal status text maps to its alarm status."""
    panel = ADTPulseAlarmPanel()
    panel.update_alarm_from_etree(status_page(f"\n  {text}\n  more text"))
    assert panel.status == expected


def test_update_keeps_transition_until_timeout():
    """A pending DISARMING survives a stale 'Armed Away' page until the timeout."""
    panel = ADTPulseAlarmPanel(_status=ADT_ALARM_DISARMING)
    panel._last_arm_disarm = int(time())
    panel.update_alarm_from_etree(status_page("Armed Away. All Quiet."))
    assert panel.status == ADT_ALARM_DISARMING

    panel._last_arm_disarm = int(time()) - int(ADT_ARM_DISARM_TIMEOUT) - 5
    panel.update_alarm_from_etree(status_page("Armed Away. All Quiet."))
    assert panel.status == ADT_ALARM_AWAY


# ---------------------------------------------------------------------------
# per-instance fields and state properties
# ---------------------------------------------------------------------------


def test_state_lock_is_per_instance():
    """Each panel has its own lock."""
    assert ADTPulseAlarmPanel()._state_lock is not ADTPulseAlarmPanel()._state_lock


def test_last_arm_disarm_is_set_at_creation():
    """_last_arm_disarm is the creation time, not the module import time."""
    with freeze_time("2031-05-06 07:08:09"):
        expected = int(time())
        panel = ADTPulseAlarmPanel()
    assert panel.last_update == expected
    assert isinstance(panel.last_update, int)


STATE_PROPERTIES = (
    "is_away",
    "is_home",
    "is_disarmed",
    "is_arming",
    "is_disarming",
    "is_armed_night",
)


@pytest.mark.parametrize(
    ("status", "true_property"),
    [
        (ADT_ALARM_AWAY, "is_away"),
        (ADT_ALARM_HOME, "is_home"),
        (ADT_ALARM_OFF, "is_disarmed"),
        (ADT_ALARM_ARMING, "is_arming"),
        (ADT_ALARM_DISARMING, "is_disarming"),
        (ADT_ALARM_NIGHT, "is_armed_night"),
        (ADT_ALARM_UNKNOWN, None),
    ],
)
def test_state_properties(status, true_property):
    """Exactly the property matching the status is True."""
    panel = ADTPulseAlarmPanel()
    panel.status = status
    assert panel.status == status
    for prop in STATE_PROPERTIES:
        assert getattr(panel, prop) is (prop == true_property), prop


def test_status_setter_rejects_unknown_value():
    """Setting an invalid status raises ValueError."""
    panel = ADTPulseAlarmPanel()
    with pytest.raises(ValueError, match="Alarm status must be one of"):
        panel.status = "Armed Home"


# ---------------------------------------------------------------------------
# arm / disarm
# ---------------------------------------------------------------------------


@pytest.fixture
def connection(get_mocked_connection_properties) -> PulseConnection:
    """Authenticated PulseConnection against the mocked portal."""
    status = PulseConnectionStatus()
    status.authenticated_flag.set()
    return PulseConnection(
        status,
        get_mocked_connection_properties,
        PulseAuthenticationProperties(
            "test@example.com", "testpassword", "testfingerprint"
        ),
    )


@pytest.fixture
def arm_responses() -> Generator[aioresponses]:
    """Mocked portal with nothing registered yet."""
    with aioresponses() as responses:
        yield responses


def add_arm_response(responses, get_mocked_url, read_file, file_name: str) -> None:
    """Register the arm/disarm POST response."""
    responses.post(
        re.compile(rf"^{re.escape(get_mocked_url(ADT_ARM_DISARM_URI))}.*$"),
        body=read_file(file_name),
        content_type="text/html",
    )


def posted_forms(responses) -> list[dict[str, str]]:
    """Return the form data of every arm/disarm POST made."""
    return [
        call.kwargs["data"]
        for (method, url), calls in responses.requests.items()
        if method == "POST" and str(url).endswith(ADT_ARM_DISARM_URI)
        for call in calls
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "mode"),
    [
        ("async_arm_away", ADT_ALARM_AWAY),
        ("async_arm_home", ADT_ALARM_HOME),
        ("async_arm_night", ADT_ALARM_NIGHT),
    ],
)
async def test_arm(method, mode, connection, arm_responses, get_mocked_url, read_file):
    """Arming from off posts setArmState and moves to ARMING."""
    add_arm_response(
        arm_responses, get_mocked_url, read_file, "arm_disarm_success.html"
    )
    panel = ADTPulseAlarmPanel(_sat=TEST_SAT, _status=ADT_ALARM_OFF)
    panel._last_arm_disarm = 0
    assert await getattr(panel, method)(connection) is True
    assert posted_forms(arm_responses) == [
        {
            "href": "rest/adt/ui/client/security/setArmState",
            "armstate": ADT_ALARM_OFF,
            "arm": mode,
            "sat": TEST_SAT,
        }
    ]
    assert panel.status == ADT_ALARM_ARMING
    assert panel.is_arming
    assert not panel.is_force_armed
    assert panel.last_update > 0
    await connection._connection_properties.clear_session()


@pytest.mark.asyncio
async def test_force_arm(connection, arm_responses, get_mocked_url, read_file):
    """force_arm posts setForceArm with armstate=forcearm."""
    add_arm_response(
        arm_responses, get_mocked_url, read_file, "arm_disarm_success.html"
    )
    panel = ADTPulseAlarmPanel(_sat=TEST_SAT, _status=ADT_ALARM_OFF)
    assert await panel.async_arm_away(connection, force_arm=True) is True
    assert posted_forms(arm_responses) == [
        {
            "href": "rest/adt/ui/client/security/setForceArm",
            "armstate": "forcearm",
            "arm": ADT_ALARM_AWAY,
            "sat": TEST_SAT,
        }
    ]
    assert panel.is_force_armed
    assert panel.status == ADT_ALARM_ARMING
    await connection._connection_properties.clear_session()


@pytest.mark.asyncio
async def test_disarm(connection, arm_responses, get_mocked_url, read_file):
    """Disarming posts setArmState from the current state and moves to DISARMING."""
    add_arm_response(
        arm_responses, get_mocked_url, read_file, "arm_disarm_success.html"
    )
    panel = ADTPulseAlarmPanel(
        _sat=TEST_SAT, _status=ADT_ALARM_AWAY, _is_force_armed=True
    )
    assert await panel.async_disarm(connection) is True
    assert posted_forms(arm_responses) == [
        {
            "href": "rest/adt/ui/client/security/setArmState",
            "armstate": ADT_ALARM_AWAY,
            "arm": ADT_ALARM_OFF,
            "sat": TEST_SAT,
        }
    ]
    assert panel.status == ADT_ALARM_DISARMING
    assert panel.is_disarming
    assert not panel.is_force_armed
    await connection._connection_properties.clear_session()


@pytest.mark.asyncio
async def test_arm_fails_on_error_block(
    connection, arm_responses, get_mocked_url, read_file, caplog
):
    """An error block in the response fails the arm and leaves the state alone."""
    add_arm_response(
        arm_responses, get_mocked_url, read_file, "arm_disarm_open_zone.html"
    )
    panel = ADTPulseAlarmPanel(_sat=TEST_SAT, _status=ADT_ALARM_OFF)
    panel._last_arm_disarm = 0
    with caplog.at_level(logging.WARNING):
        assert await panel.async_arm_away(connection) is False
    assert len(posted_forms(arm_responses)) == 1
    assert panel.status == ADT_ALARM_OFF
    assert panel.last_update == 0
    assert "Could not set alarm state to away because Back Door is open." in (
        caplog.text
    )
    assert "Arm Anyway" not in caplog.text
    await connection._connection_properties.clear_session()


@pytest.mark.asyncio
async def test_arm_http_error_leaves_state(connection, arm_responses, get_mocked_url):
    """An HTTP error propagates from the query and leaves the state alone."""
    arm_responses.post(
        re.compile(rf"^{re.escape(get_mocked_url(ADT_ARM_DISARM_URI))}.*$"),
        status=403,
    )
    panel = ADTPulseAlarmPanel(_sat=TEST_SAT, _status=ADT_ALARM_OFF)
    with pytest.raises(PulseServerConnectionError):
        await panel.async_arm_home(connection)
    assert panel.status == ADT_ALARM_OFF
    assert not panel.is_force_armed
    await connection._connection_properties.clear_session()


@pytest.mark.asyncio
async def test_arm_from_armed_state_is_rejected(connection, arm_responses, caplog):
    """Switching between armed modes is refused without sending a request."""
    panel = ADTPulseAlarmPanel(_sat=TEST_SAT, _status=ADT_ALARM_AWAY)
    with caplog.at_level(logging.WARNING):
        assert await panel.async_arm_home(connection) is False
    assert posted_forms(arm_responses) == []
    assert panel.status == ADT_ALARM_AWAY
    assert "Cannot set alarm status from away to stay" in caplog.text
