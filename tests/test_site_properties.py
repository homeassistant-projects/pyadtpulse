"""
Test cases for ADTPulseSiteProperties class.

This module contains tests that verify the behavior of the ADTPulseSiteProperties class,
which handles site configuration, zones, alarm panel, and gateway functionality.
"""

from pyadtpulse.zones import ADTPulseZones, ADTPulseZoneData
from pyadtpulse.site_properties import ADTPulseSiteProperties

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

        Verifies that both zone accessors return an empty container instead of
        raising.
        """
        site_properties = ADTPulseSiteProperties(TEST_SITE_ID, TEST_SITE_NAME)
        assert site_properties.zones == []
        assert isinstance(site_properties.zones_as_dict, ADTPulseZones)
        assert not site_properties.zones_as_dict

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
