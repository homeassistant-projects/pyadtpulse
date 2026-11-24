"""Test PyADTPulse properties."""

import pytest

from pyadtpulse.const import (
    ADT_MIN_RELOGIN_INTERVAL,
    ADT_MAX_KEEPALIVE_INTERVAL,
    ADT_DEFAULT_RELOGIN_INTERVAL,
)
from pyadtpulse.pyadtpulse_async import PyADTPulseAsync
from pyadtpulse.pyadtpulse_properties import PyADTPulseProperties


@pytest.mark.parametrize("interval", (0, ADT_MIN_RELOGIN_INTERVAL, 240))
def test_relogin_interval_valid(interval: int):
    """0 (disabled) and anything from the minimum up are accepted."""
    props = PyADTPulseProperties(relogin_interval=interval)
    assert props.relogin_interval == interval
    props.relogin_interval = None
    assert props.relogin_interval == ADT_DEFAULT_RELOGIN_INTERVAL
    props.relogin_interval = interval
    assert props.relogin_interval == interval


def test_relogin_interval_disabled_on_client():
    """The client accepts 0 to disable relogin, in the constructor and later."""
    p = PyADTPulseAsync(
        "testuser@example.com", "testpassword", "testfingerprint", relogin_interval=0
    )
    assert p.relogin_interval == 0
    p.relogin_interval = 60
    p.relogin_interval = 0
    assert p.relogin_interval == 0


@pytest.mark.parametrize("interval", (-1, 1, ADT_MIN_RELOGIN_INTERVAL - 1))
def test_relogin_interval_invalid(interval: int):
    """Positive values under the minimum, and negative ones, are rejected."""
    message = f"must be 0 \\(disabled\\) or at least {ADT_MIN_RELOGIN_INTERVAL}"
    with pytest.raises(ValueError, match=message):
        PyADTPulseProperties(relogin_interval=interval)
    props = PyADTPulseProperties()
    with pytest.raises(ValueError, match=message):
        props.relogin_interval = interval
    assert props.relogin_interval == ADT_DEFAULT_RELOGIN_INTERVAL


@pytest.mark.parametrize("interval", (1, ADT_MAX_KEEPALIVE_INTERVAL))
def test_keepalive_interval_valid(interval: int):
    """1 to the maximum are accepted, both ends included."""
    assert PyADTPulseProperties(keepalive_interval=interval).keepalive_interval == (
        interval
    )


@pytest.mark.parametrize("interval", (-1, 0, ADT_MAX_KEEPALIVE_INTERVAL + 1))
def test_keepalive_interval_invalid(interval: int):
    """Values outside 1 to the maximum are rejected, with a message that says so."""
    with pytest.raises(
        ValueError, match=f"must be between 1 and {ADT_MAX_KEEPALIVE_INTERVAL}"
    ):
        PyADTPulseProperties(keepalive_interval=interval)
