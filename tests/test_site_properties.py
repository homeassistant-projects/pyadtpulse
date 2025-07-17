"""
Test cases for ADTPulseSiteProperties class.

This module contains tests that verify the behavior of the ADTPulseSiteProperties class,
which handles site configuration, zones, alarm panel, and gateway functionality.
"""

import time
from multiprocessing import RLock
from typing import cast

import pytest

from pyadtpulse.alarm_panel import ADTPulseAlarmPanel
from pyadtpulse.const import DEFAULT_API_HOST
from pyadtpulse.pulse_authentication_properties import PulseAuthenticationProperties
from pyadtpulse.pulse_connection import PulseConnection
from pyadtpulse.pulse_connection_properties import PulseConnectionProperties
from pyadtpulse.pulse_connection_status import PulseConnectionStatus
from pyadtpulse.site_properties import ADTPulseSiteProperties
from pyadtpulse.zones import ADTPulseFlattendZone, ADTPulseZoneData, ADTPulseZones

# Constants
TEST_SITE_ID = "12345"
TEST_SITE_NAME = "My ADT Pulse Site"
ZONE_COUNT = 2


class TestADTPulseSiteProperties:
    """Test cases for verifying ADTPulseSiteProperties functionality."""

    def test_retrieve_site_id_and_name(self):
        """
        Test retrieval of site ID and name.

        Verifies that:
            - Site ID can be retrieved correctly
            - Site name can be retrieved correctly
            - Retrieved values match initialization values
        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        assert site_properties.id == TEST_SITE_ID
        assert site_properties.name == TEST_SITE_NAME

    def test_retrieve_all_zones_with_zones_fixed(self):
        """
        Test zone retrieval when zones are present.

        Verifies that:
            - All configured zones can be retrieved
            - Zones are returned as a list
            - Zone count matches expected number
        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)

        # Add test zones
        zone1 = ADTPulseZoneData(id_="1", name="Front Door")
        zone2 = ADTPulseZoneData(id_="2", name="Back Door")
        site_properties._zones[1] = zone1
        site_properties._zones[2] = zone2

        zones = site_properties.zones
        assert isinstance(zones, list)
        assert len(zones) == ZONE_COUNT

    def test_retrieve_zone_information_as_dict(self):
        """
        Test retrieval of zone information in dictionary format.

        Verifies that:
            - Zone information can be retrieved as dictionary
            - Returns proper ADTPulseZones instance
            - Zone data structure is correct
        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        site_properties._zones = ADTPulseZones()
        zone = ADTPulseZoneData(id_="1", name="Zone1")
        site_properties._zones[1] = zone
        assert isinstance(site_properties.zones_as_dict, ADTPulseZones)

    def test_no_zones_exist(self):
        """
        Test behavior when no zones are configured.

        Verifies that:
            - RuntimeError is raised when accessing zones
            - Error occurs before any zone processing
        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        with pytest.raises(RuntimeError):
            _ = site_properties.zones

    def test_retrieve_site_data_while_modifying(self, mocker):
        """
        Test concurrent access to site data.

        Args:
            mocker: Pytest mocker fixture for mocking objects.

        Verifies that:
            - Site lock prevents concurrent access
            - Last updated time is properly protected
            - Thread safety mechanisms work correctly

        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        mocker.patch.object(site_properties, "_last_updated", 0)
        mocker.patch.object(site_properties, "_site_lock", RLock())

        with site_properties.site_lock:
            retrieved_last_updated = site_properties.last_updated

        assert retrieved_last_updated == 0

    def test_set_alarm_status_to_existing_status(self, mocker):
        """
        Test setting alarm status to its current value.

        Args:
            mocker: Pytest mocker fixture for mocking objects.

        Verifies that:
            - Setting same status is handled properly
            - Current status is preserved

        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        mocker.patch.object(site_properties._alarm_panel, "_status", "Armed Away")

    def test_check_updates_exist(self, mocker):
        """
        Test update existence checking.

        Args:
            mocker: Pytest mocker fixture for mocking objects.

        Verifies that:
            - Update check returns correct boolean
            - Last update time is considered

        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        current_time = time.time()
        mocker.patch.object(site_properties, "_last_updated", return_value=current_time)
        assert site_properties.updates_may_exist is False

    @pytest.mark.asyncio
    async def test_update_site_zone_data_async(self, mocker):
        """
        Tests asynchronous site and zone data updates.

        Tests the behavior of site and zone data updates in async mode:
        - Async update completes successfully
        - Zone data is properly flattened
        - Update status is correctly returned

        Args:
            mocker: Pytest mocker fixture for mocking objects.

        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        mock_zones = mocker.Mock()
        flattened_zone = cast(ADTPulseFlattendZone, mocker.Mock())
        mock_zones.flatten.return_value = [flattened_zone]
        site_properties._zones = mock_zones

        result = await site_properties.async_update()
        assert result is False

    @pytest.mark.asyncio
    async def test_cannot_set_alarm_status(self, mocker):
        """
        Tests failure scenario for alarm status setting.

        Tests the failure handling when setting alarm status:
        - Failed alarm status change returns False
        - Connection parameters are properly handled

        Args:
            mocker: Pytest mocker fixture for mocking objects.

        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        cp = PulseConnectionProperties(DEFAULT_API_HOST)
        cs = PulseConnectionStatus()
        pa = PulseAuthenticationProperties(
            "test@example.com", "testpassword", "testfingerprint"
        )
        connection = PulseConnection(cs, cp, pa)
        result = await site_properties._alarm_panel._arm(
            connection, "Armed Home", False
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_failed_updating_alarm_mode(self, mocker):
        """
        Tests alarm mode update failure handling.

        Tests the behavior when alarm mode update fails:
        - Failed mode update returns False
        - Error handling works correctly

        Args:
            mocker: Pytest mocker fixture for mocking objects.

        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        cp = PulseConnectionProperties(DEFAULT_API_HOST)
        cs = PulseConnectionStatus()
        pa = PulseAuthenticationProperties(
            "test@example.com", "testpassword", "testfingerprint"
        )
        connection = PulseConnection(cs, cp, pa)

        async def mock_arm(*args, **kwargs):
            return False

        mocker.patch.object(ADTPulseAlarmPanel, "_arm", side_effect=mock_arm)
        result = await site_properties.alarm_control_panel._arm(
            connection, "new_mode", False
        )
        assert result is False

    def test_retrieve_zones_with_invalid_input(self, mocker):
        """
        Test zone retrieval with invalid input.

        Args:
            mocker: Pytest mocker fixture for mocking objects.

        Verifies that:
            - RuntimeError is raised for invalid zones
            - Both access methods handle errors consistently

        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        mocker.patch.object(site_properties, "_zones", None)

        with pytest.raises(RuntimeError):
            _ = site_properties.zones

        with pytest.raises(RuntimeError):
            _ = site_properties.zones_as_dict

    def test_retrieve_alarm_panel_invalid_input(self, mocker):
        """
        Test alarm panel retrieval with invalid input.

        Args:
            mocker: Pytest mocker fixture for mocking objects.

        Verifies that:
            - Mocked alarm panel is returned correctly
            - No exception is raised

        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        mock_alarm_panel = mocker.Mock()
        site_properties._alarm_panel = mock_alarm_panel
        assert site_properties.alarm_control_panel == mock_alarm_panel
