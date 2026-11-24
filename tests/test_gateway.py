"""Unit tests for the ADTPulseGateway class and its related functionality."""

import time
from ipaddress import IPv4Address

import pytest
from aioresponses import aioresponses

from pyadtpulse.site import ADTPulseSite
from pyadtpulse.const import (
    ADT_GATEWAY_URI,
    ADT_GATEWAY_STRING,
    ADT_DEFAULT_POLL_INTERVAL,
    ADT_GATEWAY_MAX_OFFLINE_POLL_INTERVAL,
)
from pyadtpulse.gateway import ADTPulseGateway
from pyadtpulse.pulse_connection import PulseConnection
from pyadtpulse.pulse_connection_status import PulseConnectionStatus
from pyadtpulse.pulse_authentication_properties import PulseAuthenticationProperties


# ADTPulseGateway object can be created with default values
def test_default_values():
    """Test that ADTPulseGateway object can be created with default values."""
    gateway = ADTPulseGateway()
    assert gateway.manufacturer == "Unknown"
    assert gateway._status_text == "OFFLINE"
    assert gateway.backoff._name == "Gateway"
    assert gateway.backoff._initial_backoff_interval == ADT_DEFAULT_POLL_INTERVAL
    assert (
        gateway.backoff._max_backoff_interval == ADT_GATEWAY_MAX_OFFLINE_POLL_INTERVAL
    )
    assert gateway.backoff._backoff_count == 0
    assert gateway.backoff._expiration_time == 0.0
    assert gateway.backoff._detailed_debug_logging is False
    assert gateway.backoff._threshold == 0
    assert gateway.model is None
    assert gateway.serial_number is None
    assert gateway.next_update == 0
    assert gateway.last_update == 0
    assert gateway.firmware_version is None
    assert gateway.hardware_version is None
    assert gateway.primary_connection_type is None
    assert gateway.broadband_connection_status is None
    assert gateway.cellular_connection_status is None
    assert gateway._cellular_connection_signal_strength == 0.0
    assert gateway.broadband_lan_ip_address is None
    assert gateway._broadband_lan_mac is None
    assert gateway.device_lan_ip_address is None
    assert gateway._device_lan_mac is None
    assert gateway.router_lan_ip_address is None
    assert gateway.router_wan_ip_address is None


# is_online property returns correct online status
def test_is_online_property():
    """Test that is_online property returns correct online status."""
    gateway = ADTPulseGateway()
    assert gateway.is_online is False
    gateway.is_online = True
    assert gateway.is_online is True
    gateway.is_online = False
    assert gateway.is_online is False


# poll_interval property can be set and returns correct value
def test_poll_interval_property():
    """Test that poll_interval property can be set and returns correct value."""
    gateway = ADTPulseGateway()
    assert gateway.poll_interval == ADT_DEFAULT_POLL_INTERVAL
    gateway.poll_interval = 60.0
    assert gateway.poll_interval == 60.0


# gateway MAC addresses can be set and retrieved
def test_gateway_mac_addresses():
    """Test that gateway MAC addresses can be set and retrieved."""
    gateway = ADTPulseGateway()
    gateway.broadband_lan_mac = "00:11:22:33:44:55"
    assert gateway.broadband_lan_mac == "00:11:22:33:44:55"
    gateway.device_lan_mac = "AA:BB:CC:DD:EE:FF"
    assert gateway.device_lan_mac == "AA:BB:CC:DD:EE:FF"


# cellular connection signal strength can be set and retrieved
def test_cellular_connection_signal_strength():
    """Test that cellular connection signal strength can be set and retrieved."""
    gateway = ADTPulseGateway()
    gateway.cellular_connection_signal_strength = -70.5
    assert gateway.cellular_connection_signal_strength == -70.5


# set_gateway_attributes method sets attributes correctly
def test_set_gateway_attributes_sets_attributes_correctly():
    """Test that set_gateway_attributes method sets attributes correctly."""
    gateway = ADTPulseGateway()
    attributes = {
        "manufacturer": "ADT",
        "model": "1234",
        "serial_number": "5678",
        "firmware_version": "1.0",
        "hardware_version": "2.0",
        "primary_connection_type": "Ethernet",
        "broadband_connection_status": "Connected",
        "cellular_connection_status": "Connected",
        "broadband_lan_mac": "00:11:22:33:44:55",
        "device_lan_mac": "AA:BB:CC:DD:EE:FF",
        "cellular_signal_strength": "4.5",
    }

    gateway.set_gateway_attributes(attributes)

    assert gateway.manufacturer == "ADT"
    assert gateway.model == "1234"
    assert gateway.serial_number == "5678"
    assert gateway.firmware_version == "1.0"
    assert gateway.hardware_version == "2.0"
    assert gateway.primary_connection_type == "Ethernet"
    assert gateway.broadband_connection_status == "Connected"
    assert gateway.cellular_connection_status == "Connected"
    assert gateway.broadband_lan_mac == "00:11:22:33:44:55"
    assert gateway.device_lan_mac == "AA:BB:CC:DD:EE:FF"
    assert gateway.cellular_connection_signal_strength == 4.5


# backoff object can be incremented and reset correctly
def test_backoff_increment_and_reset():
    """Test that backoff object can be incremented and reset correctly."""
    gateway = ADTPulseGateway()

    # Increment backoff count
    gateway.backoff.increment_backoff()
    assert gateway.backoff._backoff_count == 1

    # Reset backoff count
    gateway.backoff.reset_backoff()
    assert gateway.backoff._backoff_count == 0


# is_online property returns correct offline status when set to False
def test_is_online_returns_correct_offline_status_when_set_to_false():
    """Test that is_online property returns correct offline status when set to False."""
    gateway = ADTPulseGateway()
    gateway.is_online = False
    assert gateway.is_online is False


# poll_interval property raises ValueError when set to 0
def test_poll_interval_raises_value_error_when_set_to_0():
    """Test that poll_interval property raises ValueError when set to 0."""
    gateway = ADTPulseGateway()
    with pytest.raises(ValueError):
        gateway.poll_interval = 0


# backoff object can wait for correct amount of time before returning
@pytest.mark.asyncio
async def test_backoff_wait_time(mock_sleep):
    """Test that backoff object can wait for correct amount of time before returning."""
    # Arrange
    gateway = ADTPulseGateway()
    gateway.backoff._backoff_count = 1
    gateway.backoff._threshold = 0
    gateway.backoff._initial_backoff_interval = 5.0
    gateway.backoff._max_backoff_interval = 10.0
    gateway.backoff._expiration_time = 0.0

    # Act
    await gateway.backoff.async_wait_for_backoff()

    # Assert
    mock_sleep.assert_awaited_once_with(5.0)


def test_set_gateway_attributes_empty_string_fixed():
    """
    Gateway Attributes test.

    Test that set_gateway_attributes method
    sets attributes to None when given an empty string
    """
    gateway = ADTPulseGateway()
    gateway.set_gateway_attributes(
        {"model": "", "serial_number": "", "firmware_version": ""}
    )
    assert gateway.model is None
    assert gateway.serial_number is None
    assert gateway.firmware_version is None


def test_cellular_connection_signal_strength_to_zero():
    """Test that cellular connection signal strength can be set to 0.0."""
    gateway = ADTPulseGateway()
    gateway.cellular_connection_signal_strength = 0.0
    assert gateway.cellular_connection_signal_strength == 0.0


def test_poll_interval_raises_value_error():
    """
    Poll interval property raises ValueError.

    Test that poll_interval property raises ValueError
    when set to a value greater than ADT_GATEWAY_MAX_OFFLINE_POLL_INTERVAL.
    """
    gateway = ADTPulseGateway()
    with pytest.raises(ValueError):
        gateway.poll_interval = ADT_GATEWAY_MAX_OFFLINE_POLL_INTERVAL + 1


def test_set_gateway_attributes_valid_value():
    """
    Set_gateway_attributes test.

    Test that set_gateway_attributes method
    sets attributes to a valid value when given a valid value.
    """
    gateway = ADTPulseGateway()
    gateway.set_gateway_attributes({"broadband_lan_mac": "00:0a:95:9d:68:16"})
    assert gateway.broadband_lan_mac == "00:0a:95:9d:68:16"


def test_set_gateway_attributes_invalid_ip():
    """
    Set_gateway_attributes test.

    Test that set_gateway_attributes method
    sets IP address attributes to None when given an invalid IP address.
    """
    gateway = ADTPulseGateway()
    gateway.set_gateway_attributes({"broadband_lan_ip_address": "invalid_ip"})
    assert gateway.broadband_lan_ip_address is None
    gateway.set_gateway_attributes({"device_lan_ip_address": "invalid_ip"})
    assert gateway.device_lan_ip_address is None
    gateway.set_gateway_attributes({"router_lan_ip_address": "invalid_ip"})
    assert gateway.router_lan_ip_address is None
    gateway.set_gateway_attributes({"router_wan_ip_address": "invalid_ip"})
    assert gateway.router_wan_ip_address is None


# gateway MAC addresses raise ValueError when set to an invalid MAC address
def test_gateway_mac_address_invalid():
    """Test that setting an invalid MAC address raises a ValueError."""
    gateway = ADTPulseGateway()
    with pytest.raises(ValueError):
        gateway.broadband_lan_mac = "00:00:00:00:00:00:00"
    with pytest.raises(ValueError):
        gateway.device_lan_mac = "00:00:00:00:00:00:00"


# is_online property can be set to True and False
def test_is_online_property_true_and_false():
    """Test that is_online property can be set to True and False."""
    gateway = ADTPulseGateway()

    # Test setting is_online to True
    gateway.is_online = True
    assert gateway.is_online is True
    assert gateway._status_text == "ONLINE"

    # Test setting is_online to False
    gateway.is_online = False
    assert gateway.is_online is False
    assert gateway._status_text == "OFFLINE"


# poll_interval property can be set to a custom value
def test_poll_interval_custom_value():
    """Test that poll_interval property can be set to a custom value."""
    gateway = ADTPulseGateway()
    custom_interval = 10.0
    gateway.poll_interval = custom_interval
    assert gateway.poll_interval == custom_interval


# ADTPulseGateway object can be created with custom values
def test_custom_values():
    """Test that ADTPulseGateway object can be created with custom values."""
    gateway = ADTPulseGateway(
        manufacturer="Custom Manufacturer",
        _status_text="CUSTOM_STATUS",
        model="Custom Model",
        serial_number="Custom Serial Number",
        next_update=1234567890,
        last_update=9876543210,
        firmware_version="Custom Firmware Version",
        hardware_version="Custom Hardware Version",
        primary_connection_type="Custom Connection Type",
        broadband_connection_status="Custom Broadband Status",
        cellular_connection_status="Custom Cellular Status",
        _cellular_connection_signal_strength=0.5,
        broadband_lan_ip_address=IPv4Address("192.168.0.1"),
        _broadband_lan_mac="00:11:22:33:44:55",
        device_lan_ip_address=IPv4Address("192.168.0.2"),
        _device_lan_mac="AA:BB:CC:DD:EE:FF",
        router_lan_ip_address=IPv4Address("192.168.1.1"),
        router_wan_ip_address=IPv4Address("10.0.0.1"),
    )

    assert gateway.manufacturer == "Custom Manufacturer"
    assert gateway._status_text == "CUSTOM_STATUS"
    assert gateway.backoff._name == "Gateway"
    assert gateway.backoff._initial_backoff_interval == ADT_DEFAULT_POLL_INTERVAL
    assert (
        gateway.backoff._max_backoff_interval == ADT_GATEWAY_MAX_OFFLINE_POLL_INTERVAL
    )
    assert gateway.backoff._backoff_count == 0
    assert gateway.backoff._expiration_time == 0.0
    assert gateway.backoff._detailed_debug_logging is False
    assert gateway.backoff._threshold == 0
    assert gateway.model == "Custom Model"
    assert gateway.serial_number == "Custom Serial Number"
    assert gateway.next_update == 1234567890
    assert gateway.last_update == 9876543210
    assert gateway.firmware_version == "Custom Firmware Version"
    assert gateway.hardware_version == "Custom Hardware Version"
    assert gateway.primary_connection_type == "Custom Connection Type"
    assert gateway.broadband_connection_status == "Custom Broadband Status"
    assert gateway.cellular_connection_status == "Custom Cellular Status"
    assert gateway._cellular_connection_signal_strength == 0.5
    assert gateway.broadband_lan_ip_address == IPv4Address("192.168.0.1")
    assert gateway._broadband_lan_mac == "00:11:22:33:44:55"
    assert gateway.device_lan_ip_address == IPv4Address("192.168.0.2")
    assert gateway._device_lan_mac == "AA:BB:CC:DD:EE:FF"
    assert gateway.router_lan_ip_address == IPv4Address("192.168.1.1")
    assert gateway.router_wan_ip_address == IPv4Address("10.0.0.1")


def test_set_gateway_attributes_unparseable_datetime_keeps_int():
    """'N/A', empty or missing update times reset to 0 instead of None."""
    gateway = ADTPulseGateway(next_update=1234, last_update=5678)
    gateway.set_gateway_attributes({"next_update": "N/A", "last_update": ""})
    assert gateway.next_update == 0
    assert gateway.last_update == 0
    gateway.next_update = 1234
    gateway.set_gateway_attributes({})
    assert gateway.next_update == 0
    # the keepalive compares this to time.time(); None raised TypeError here
    assert gateway.next_update < time.time()


def test_set_gateway_attributes_missing_values_keep_defaults():
    """Missing values reset every attribute to its declared default."""
    gateway = ADTPulseGateway(
        model="m", _cellular_connection_signal_strength=3.0, next_update=1
    )
    gateway.set_gateway_attributes({})
    assert gateway.model is None
    assert gateway.cellular_connection_signal_strength == 0.0
    assert gateway.next_update == 0
    assert gateway.last_update == 0
    assert gateway.broadband_lan_ip_address is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("-71 dBm", -71.0),
        ("4.5", 4.5),
        ("3 bars", 3.0),
        ("N/A", 0.0),
        ("", 0.0),
        ("Unknown", 0.0),
    ],
)
def test_set_gateway_attributes_cellular_signal_strength(value, expected):
    """The portal's Cellular Signal Strength row is parsed into a float."""
    gateway = ADTPulseGateway(_cellular_connection_signal_strength=9.0)
    gateway.set_gateway_attributes({"cellular_signal_strength": value})
    assert gateway.cellular_connection_signal_strength == expected


def test_set_gateway_attributes_invalid_mac_keeps_default():
    """A MAC address the setter rejects (e.g. 'N/A') resets to None."""
    gateway = ADTPulseGateway(_device_lan_mac="AA:BB:CC:DD:EE:FF")
    gateway.set_gateway_attributes({"device_lan_mac": "N/A"})
    assert gateway.device_lan_mac is None


@pytest.fixture
def gateway_site(get_mocked_connection_properties) -> ADTPulseSite:
    """Site with an authenticated connection to the mocked portal."""
    status = PulseConnectionStatus()
    status.authenticated_flag.set()
    connection = PulseConnection(
        status,
        get_mocked_connection_properties,
        PulseAuthenticationProperties(
            "test@example.com", "testpassword", "testfingerprint"
        ),
    )
    return ADTPulseSite(connection, "160301za524548", "Robert Lippmann")


async def load_gateway_page(site, get_mocked_url, read_file, file_name):
    """Serve file_name as the gateway page and parse it into site.gateway."""
    with aioresponses() as responses:
        responses.get(
            get_mocked_url(ADT_GATEWAY_URI),
            body=read_file(file_name),
            content_type="text/html",
        )
        await site.async_set_device(ADT_GATEWAY_STRING)
    await site._pulse_connection._connection_properties.async_clear_session()
    return site.gateway


@pytest.mark.asyncio
async def test_gateway_page(gateway_site, get_mocked_url, read_file):
    """The saved gateway page fills the gateway attributes with typed values."""
    gateway = await load_gateway_page(
        gateway_site, get_mocked_url, read_file, "gateway.html"
    )
    assert gateway.model == "PGZNG1"
    assert gateway.serial_number == "5U020CN3007E3"
    assert isinstance(gateway.next_update, int)
    assert gateway.next_update > 0
    assert isinstance(gateway.last_update, int)
    assert gateway.last_update > 0
    assert gateway.primary_connection_type == "Broadband"
    assert gateway.cellular_connection_status == "N/A"
    assert gateway.cellular_connection_signal_strength == 0.0
    assert gateway.broadband_lan_ip_address == IPv4Address("192.168.1.31")
    assert gateway.device_lan_mac == "a4:11:62:35:07:97"


@pytest.mark.asyncio
async def test_gateway_page_cellular(gateway_site, get_mocked_url, read_file):
    """
    A gateway on cellular with an 'N/A' next update and MAC parses cleanly.

    gateway_cellular.html is gateway.html with the Next Update row set to
    "N/A", the connection type set to Cellular, the Cellular Signal Strength
    row set to "-71 dBm" and the Device LAN MAC set to "N/A".
    """
    gateway = await load_gateway_page(
        gateway_site, get_mocked_url, read_file, "gateway_cellular.html"
    )
    assert gateway.next_update == 0
    assert gateway.last_update > 0
    assert gateway.primary_connection_type == "Cellular"
    assert gateway.cellular_connection_status == "Active"
    assert gateway.cellular_connection_signal_strength == -71.0
    assert gateway.device_lan_mac is None
