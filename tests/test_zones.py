"""Test suite for ADTPulseZoneData and ADTPulseFlattendZone classes."""

from datetime import datetime

import pytest
from typeguard import TypeCheckError

from pyadtpulse.zones import (
    ADT_NAME_TO_DEFAULT_TAGS,
    ADTPulseZones,
    ADTPulseZoneData,
    ADTPulseFlattendZone,
)


class TestADTPulseZoneData:
    """Test suite for ADTPulseZoneData class."""

    # Creating an instance of ADTPulseZoneData with required parameters should succeed.
    def test_create_instance_with_required_parameters(self):
        """
        Test creating an instance with required parameters.

        Verifies that creating an ADTPulseZoneData instance with required parameters
        succeeds and sets default values correctly.
        """
        # Arrange
        name = "Zone 1"
        id_ = "zone1"

        # Act
        zone_data = ADTPulseZoneData(name, id_)

        # Assert
        assert zone_data.name == name
        assert zone_data.id_ == id_
        assert zone_data.tags == ADT_NAME_TO_DEFAULT_TAGS["Window"]
        assert zone_data.status == "Unknown"
        assert zone_data.state == "Unknown"
        assert zone_data.last_activity_timestamp == 0

    def test_set_last_activity_timestamp_greater_than_or_equal_to_1420070400(self):
        """
        Test setting valid last_activity_timestamp.

        Verifies that setting last_activity_timestamp with a value >= 1420070400
        succeeds.
        """
        # Arrange
        zone_data = ADTPulseZoneData("Zone 1", "zone1")
        timestamp = 1420070400

        # Act
        zone_data.last_activity_timestamp = timestamp

        # Assert
        assert zone_data.last_activity_timestamp == timestamp

    # Setting the tags with a valid value should succeed.
    def test_set_tags_with_valid_value(self):
        """
        Test setting valid tags.

        Verifies that setting valid tags succeeds and correctly updates the tags
        attribute.
        """
        # Arrange
        zone_data = ADTPulseZoneData("Zone 1", "zone1")
        tags = ("sensor", "doorWindow")

        # Act
        zone_data.tags = tags

        # Assert
        assert zone_data.tags == tags

    # Getting the last_activity_timestamp should return the correct value.
    def test_get_last_activity_timestamp(self):
        """
        Test getting last_activity_timestamp.

        Verifies that getting last_activity_timestamp returns the correct value
        after setting.
        """
        # Arrange
        timestamp = 1420070400
        zone_data = ADTPulseZoneData("Zone 1", "zone1")
        zone_data.last_activity_timestamp = timestamp

        # Act
        result = zone_data.last_activity_timestamp

        # Assert
        assert result == timestamp

    # Getting the tags should return the correct value.
    def test_get_tags_fixed(self):
        """
        Test getting tags.

        Verifies that getting the tags returns the correct value after setting.
        """
        # Arrange
        tags = ("sensor", "doorWindow")
        zone_data = ADTPulseZoneData("Zone 1", "zone1")
        zone_data.tags = tags

        # Act
        result = zone_data.tags

        # Assert
        assert result == tags

    # ADT_NAME_TO_DEFAULT_TAGS should be a valid dictionary.
    def test_ADT_NAME_TO_DEFAULT_TAGS_is_valid_dictionary(self):
        """Test that ADT_NAME_TO_DEFAULT_TAGS is a valid dictionary."""
        # Arrange

        # Act

        # Assert
        assert isinstance(ADT_NAME_TO_DEFAULT_TAGS, dict)

    # Creating an instance of ADTPulseZoneData without required parameters should fail.
    def test_create_instance_without_required_parameters(self):
        """
        ADTPulseZoneData test.

        Test that creating an instance of ADTPulseZoneData
        without required parameters fails.
        """
        # Arrange

        # Act and Assert
        with pytest.raises(TypeError):
            ADTPulseZoneData()  # type: ignore

    # Setting the tags with an invalid value should raise a ValueError.
    def test_set_tags_with_invalid_value(self):
        """Test that setting the tags with an invalid value raises a ValueError."""
        # Arrange
        zone_data = ADTPulseZoneData("Zone 1", "zone1")
        tags = ("InvalidSensor", "InvalidType")

        # Act and Assert
        with pytest.raises(ValueError):
            zone_data.tags = tags

    # Getting the name should return the correct value.
    def test_get_name(self):
        """Test that getting the name returns the correct value."""
        # Arrange
        name = "Zone 1"
        zone_data = ADTPulseZoneData(name, "zone1")

        # Act
        result = zone_data.name

        # Assert
        assert result == name

    # Getting the id_ should return the correct value.
    def test_get_id(self):
        """Test that getting the id_ returns the correct value."""
        # Arrange
        id_ = "zone1"
        zone_data = ADTPulseZoneData("Zone 1", id_)

        # Act
        result = zone_data.id_

        # Assert
        assert result == id_

    # Setting the status with a valid value should succeed.
    def test_set_status_with_valid_value(self):
        """Test that setting the status with a valid value succeeds."""
        # Arrange
        zone_data = ADTPulseZoneData("Zone 1", "zone1")
        status = "Online"

        # Act
        zone_data.status = status

        # Assert
        assert zone_data.status == status

    # Setting the state with a valid value should succeed.
    def test_setting_state_with_valid_value(self):
        """Test that setting the state with a valid value succeeds."""
        # Arrange
        name = "Zone 1"
        id_ = "zone1"
        state = "Opened"

        # Act
        zone_data = ADTPulseZoneData(name, id_)
        zone_data.state = state

        # Assert
        assert zone_data.state == state

    # Getting the status should return the correct value.
    def test_getting_status(self):
        """Test that getting the status returns the correct value."""
        # Arrange
        name = "Zone 1"
        id_ = "zone1"
        status = "Online"

        # Act
        zone_data = ADTPulseZoneData(name, id_)
        zone_data.status = status

        # Assert
        assert zone_data.status == status

    # Getting the state should return the correct value.
    def test_getting_state_returns_correct_value(self):
        """Test that getting the state returns the correct value."""
        # Arrange
        name = "Zone 1"
        id_ = "zone1"
        state = "Opened"

        zone_data = ADTPulseZoneData(name, id_)
        zone_data.state = state

        # Act
        result = zone_data.state

        # Assert
        assert result == state


class TestADTPulseFlattendZone:
    """
    Test suite for ADTPulseFlattendZone class.

    Tests initialization, attribute access, and modification of flattened zone data.
    """

    def test_init_valid_params(self):
        """
        Test creating instance with valid parameters.

        Verifies that an object is created with correct attributes.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp

    def test_attribute_access(self):
        """
        Test attribute access functionality.

        Ensures attributes return expected values.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Act & Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp

    def test_attribute_modification(self):
        """
        Test attribute modification.

        Verifies that modifying instance attributes updates values correctly.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Act
        new_zone = 2
        new_name = "Zone 2"
        new_id = "zone2"
        new_tags = ("sensor2", "type2")
        new_status = "Offline"
        new_state = "Closed"
        new_last_activity_timestamp = 9876543210

        zone_obj["zone"] = new_zone
        zone_obj["name"] = new_name
        zone_obj["id_"] = new_id
        zone_obj["tags"] = new_tags
        zone_obj["status"] = new_status
        zone_obj["state"] = new_state
        zone_obj["last_activity_timestamp"] = new_last_activity_timestamp

        # Assert
        assert zone_obj["zone"] == new_zone
        assert zone_obj["name"] == new_name
        assert zone_obj["id_"] == new_id
        assert zone_obj["tags"] == new_tags
        assert zone_obj["status"] == new_status
        assert zone_obj["state"] == new_state
        assert zone_obj["last_activity_timestamp"] == new_last_activity_timestamp

    def test_non_integer_zone(self):
        """
        Test zone value type validation.

        Verifies that instance creation with non-integer zone value succeeds.
        """
        # Arrange
        zone = "1"
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act & Assert
        ADTPulseFlattendZone(
            zone=zone,  # type: ignore
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

    def test_empty_name(self):
        """
        Test empty name validation.

        Verifies that instance creation with empty name value succeeds.
        """
        # Arrange
        zone = 1
        name = ""
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act & Assert
        ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

    def test_empty_id(self):
        """
        Test empty ID validation.

        Verifies that instance creation with empty ID value succeeds.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = ""
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act
        ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert True

    def test_non_string_tags(self):
        """
        Test tags value type validation.

        Verifies that instance creation with non-string tag values succeeds.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", 2)
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act & Assert
        ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

    def test_non_string_status(self):
        """
        Test status value type validation.

        Verifies that instance creation with non-string status value succeeds.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = 1
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act & Assert
        ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,  # type: ignore
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

    def test_non_string_state(self):
        """
        Test state value type validation.

        Verifies that instance creation with non-string state value succeeds.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = 1
        last_activity_timestamp = 1234567890

        # Act & Assert
        ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,  # type: ignore
            last_activity_timestamp=last_activity_timestamp,
        )

    def test_non_integer_last_activity_timestamp(self):
        """
        Test timestamp value type validation.

        Verifies that instance creation with non-integer timestamp succeeds.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = "1234567890"

        # Act & Assert
        ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,  # type: ignore
        )

    def test_large_zone_fixed(self):
        """
        Test large zone value handling.

        Verifies that instance creation with very large zone value succeeds.
        """
        # Arrange
        zone = 9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999  # noqa: E501
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp

    def test_long_name_fixed(self):
        """
        Test long name value handling.

        Verifies that instance creation with very long name value succeeds.
        """
        # Arrange
        zone = 1
        name = "This is a very long name that exceeds the maximum length allowed for the 'name' attribute in ADTPulseFlattendZone"  # noqa: E501
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp

    def test_long_id_fixed(self):
        """
        Test long ID value handling.

        Verifies that instance creation with very long ID value succeeds.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "a" * 1000  # Very long string for 'id_'
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp

    def test_create_instance_with_multiple_tags_fixed(self):
        """
        ADTPulseFlattendZone test.

        Test that creating a new instance of ADTPulseFlattendZone with a tuple
        that contains multiple strings for 'tags' successfully
        creates an object with the correct attributes.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1", "sensor2", "type2")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp

    def test_long_status_string_fixed(self):
        """
        ADTPulseFlattendZone test.

        Test that creating a new instance of ADTPulseFlattendZone
        with a very long string for 'status' successfully
        creates an object with the correct attributes.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Very long status string" * 1000
        state = "Opened"
        last_activity_timestamp = 1234567890

        # Act
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp

    def test_long_state_string_fixed(self):
        """
        ADTPulseFlattendZone test.

        Test that creating a new instance of ADTPulseFlattendZone
        with a very long string for 'state' successfully
        creates an object with the correct attributes.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "a" * 1000  # Very long string for 'state'
        last_activity_timestamp = 1234567890

        # Act
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp

    def test_large_last_activity_timestamp_fixed(self):
        """
        ADTPulseFlattendZone test.

        Test that creating a new instance of ADTPulseFlattendZone
        with a very large integer value for 'last_activity_timestamp' successfully
        creates an object with the correct attributes.
        """
        # Arrange
        zone = 1
        name = "Zone 1"
        id_ = "zone1"
        tags = ("sensor1", "type1")
        status = "Online"
        state = "Opened"
        last_activity_timestamp = 999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999  # noqa: E501

        # Act
        zone_obj = ADTPulseFlattendZone(
            zone=zone,
            name=name,
            id_=id_,
            tags=tags,
            status=status,
            state=state,
            last_activity_timestamp=last_activity_timestamp,
        )

        # Assert
        assert zone_obj["zone"] == zone
        assert zone_obj["name"] == name
        assert zone_obj["id_"] == id_
        assert zone_obj["tags"] == tags
        assert zone_obj["status"] == status
        assert zone_obj["state"] == state
        assert zone_obj["last_activity_timestamp"] == last_activity_timestamp


class TestADTPulseZones:
    """
    ADTPulseZones test class.

    ADTPulseZones can be initialized with a dictionary
    containing ADTPulseZoneData with zone as the key.
    """

    def test_initialized_with_dictionary(self):
        """
        Test initialization with dictionary.

        Verifies that ADTPulseZones can be initialized with a dictionary of
        ADTPulseZoneData objects using zone numbers as keys.
        """
        # Arrange
        data = {
            1: ADTPulseZoneData("Zone 1", "sensor-1"),
            2: ADTPulseZoneData("Zone 2", "sensor-2"),
            3: ADTPulseZoneData("Zone 3", "sensor-3"),
        }

        # Act
        zones = ADTPulseZones(data)

        # Assert
        assert len(zones) == 3
        assert zones[1].name == "Zone 1"
        assert zones[2].name == "Zone 2"
        assert zones[3].name == "Zone 3"

    # ADTPulseZones can get a Zone by its id
    def test_get_zone_by_id(self):
        """
        Test zone retrieval by ID.

        Verifies that zones can be accessed using their numeric IDs.
        """
        # Arrange
        zones = ADTPulseZones(
            {
                1: ADTPulseZoneData("Zone 1", "sensor-1"),
                2: ADTPulseZoneData("Zone 2", "sensor-2"),
                3: ADTPulseZoneData("Zone 3", "sensor-3"),
            }
        )

        # Act
        zone_1 = zones[1]
        zone_2 = zones[2]
        zone_3 = zones[3]

        # Assert
        assert zone_1.name == "Zone 1"
        assert zone_2.name == "Zone 2"
        assert zone_3.name == "Zone 3"

    # ADTPulseZones can set a Zone by its id
    def test_set_zone_by_id(self):
        """Test that ADTPulseZones can set a Zone by its id."""
        # Arrange
        zones = ADTPulseZones()

        # Act
        zones[1] = ADTPulseZoneData("Zone 1", "sensor-1")
        zones[2] = ADTPulseZoneData("Zone 2", "sensor-2")
        zones[3] = ADTPulseZoneData("Zone 3", "sensor-3")

        # Assert
        assert len(zones) == 3
        assert zones[1].name == "Zone 1"
        assert zones[2].name == "Zone 2"
        assert zones[3].name == "Zone 3"

    # ADTPulseZones can update zone status by its id
    def test_update_zone_status(self):
        """
        Test zone status update.

        Verifies that zone status can be updated for specific zone IDs.
        """
        # Arrange
        zones = ADTPulseZones(
            {
                1: ADTPulseZoneData("Zone 1", "sensor-1"),
                2: ADTPulseZoneData("Zone 2", "sensor-2"),
                3: ADTPulseZoneData("Zone 3", "sensor-3"),
            }
        )

        # Act
        zones.update_status(1, "Online")
        zones.update_status(2, "Low Battery")
        zones.update_status(3, "Offline")

        # Assert
        assert zones[1].status == "Online"
        assert zones[2].status == "Low Battery"
        assert zones[3].status == "Offline"

    # ADTPulseZones can update zone state by its id
    def test_update_zone_state(self):
        """Test that ADTPulseZones can update zone state by its id."""
        # Arrange
        zones = ADTPulseZones(
            {
                1: ADTPulseZoneData("Zone 1", "sensor-1"),
                2: ADTPulseZoneData("Zone 2", "sensor-2"),
                3: ADTPulseZoneData("Zone 3", "sensor-3"),
            }
        )

        # Act
        zones.update_state(1, "Opened")
        zones.update_state(2, "Closed")
        zones.update_state(3, "Unknown")

        # Assert
        assert zones[1].state == "Opened"
        assert zones[2].state == "Closed"
        assert zones[3].state == "Unknown"

    # ADTPulseZones can update last activity timestamp by its id
    def test_update_last_activity_timestamp(self):
        """Test that ADTPulseZones can update last activity timestamp by its id."""
        # Arrange
        zones = ADTPulseZones(
            {
                1: ADTPulseZoneData("Zone 1", "sensor-1"),
                2: ADTPulseZoneData("Zone 2", "sensor-2"),
                3: ADTPulseZoneData("Zone 3", "sensor-3"),
            }
        )

        # Act
        dt_1 = datetime(2022, 1, 1, 12, 0, 0)
        dt_2 = datetime(2022, 1, 2, 12, 0, 0)
        dt_3 = datetime(2022, 1, 3, 12, 0, 0)

        zones.update_last_activity_timestamp(1, dt_1)
        zones.update_last_activity_timestamp(2, dt_2)
        zones.update_last_activity_timestamp(3, dt_3)

        # Assert
        assert zones[1].last_activity_timestamp == int(dt_1.timestamp())
        assert zones[2].last_activity_timestamp == int(dt_2.timestamp())
        assert zones[3].last_activity_timestamp == int(dt_3.timestamp())

    # ADTPulseZones can update device info by its id
    def test_update_device_info_by_id(self):
        """
        Test device info update.

        Verifies that device info (state and status) can be updated by zone ID.
        """
        # Arrange
        zones = ADTPulseZones()
        zones[1] = ADTPulseZoneData("Zone 1", "sensor-1")

        # Act
        zones.update_device_info(1, "Opened", "Low Battery")

        # Assert
        assert zones[1].state == "Opened"
        assert zones[1].status == "Low Battery"

    def test_update_zone_attributes_with_dictionary(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones can update zone attributes
        with a dictionary containing zone attributes.
        """
        # Arrange
        zones = ADTPulseZones()
        dev_attr = {
            "name": "Zone 1",
            "type_model": "Window Sensor",
            "zone": "1",
            "status": "Online",
        }

        # Act
        zones.update_zone_attributes(dev_attr)

        # Assert
        assert len(zones) == 1
        assert zones[1].name == "Zone 1"
        assert zones[1].id_ == "sensor-1"
        assert zones[1].tags == ADT_NAME_TO_DEFAULT_TAGS["Window"]
        assert zones[1].status == "Online"
        assert zones[1].state == "Unknown"
        assert zones[1].last_activity_timestamp == 0

    def test_key_not_int(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones raises a KeyError
        if the key is not an int when getting or setting a Zone.
        """
        # Arrange
        zones = ADTPulseZones()
        valid_key = 1
        invalid_key = "1"
        value = ADTPulseZoneData("Zone 1", "sensor-1")

        # Act
        zones[valid_key] = value

        # Assert
        with pytest.raises(KeyError):
            zones[invalid_key]  # type: ignore

    # ADTPulseZones can flatten its data into a list of ADTPulseFlattendZone
    def test_flatten_method(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones can flatten
        its data into a list of ADTPulseFlattendZone.
        """
        # Arrange
        zones = ADTPulseZones()
        zones[1] = ADTPulseZoneData("Zone 1", "sensor-1")
        zones[2] = ADTPulseZoneData("Zone 2", "sensor-2")
        zones[3] = ADTPulseZoneData("Zone 3", "sensor-3")

        # Act
        flattened_zones = zones.flatten()

        # Assert
        assert len(flattened_zones) == 3
        assert flattened_zones[0]["zone"] == 1
        assert flattened_zones[0]["name"] == "Zone 1"
        assert flattened_zones[0]["id_"] == "sensor-1"
        assert flattened_zones[1]["zone"] == 2
        assert flattened_zones[1]["name"] == "Zone 2"
        assert flattened_zones[1]["id_"] == "sensor-2"
        assert flattened_zones[2]["zone"] == 3
        assert flattened_zones[2]["name"] == "Zone 3"
        assert flattened_zones[2]["id_"] == "sensor-3"

    def test_raises_value_error_if_value_not_adtpulsezonedata(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones raises a ValueError
        if the value is not ADTPulseZoneData when setting a Zone.
        """
        # Arrange
        zones = ADTPulseZones()

        # Act and Assert
        with pytest.raises(ValueError):
            zones[1] = "Invalid Zone Data"  # type: ignore

    def test_raises_value_error_when_setting_zone_with_non_adtpulsezonedata_value(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones raises a ValueError
        when setting a Zone with a non-ADTPulseZoneData value.
        """
        # Arrange
        zones = ADTPulseZones()
        key = 1
        value = "Not ADTPulseZoneData"

        # Act & Assert
        with pytest.raises(ValueError):
            zones[key] = value  # type: ignore

    # ADTPulseZones raises a ValueError when setting a Zone with a string value
    def test_raises_value_error_when_setting_zone_with_string_value(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones raises a ValueError
        when setting a Zone with a string value.
        """
        # Arrange
        zones = ADTPulseZones()

        # Act and Assert
        with pytest.raises(ValueError):
            zones[1] = "Zone 1"  # type: ignore

    # ADTPulseZones raises a ValueError when setting a Zone with a list value
    def test_raises_value_error_when_setting_zone_with_list_value(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones raises a ValueError
        when setting a Zone with a list value.
        """
        # Arrange
        zones = ADTPulseZones()
        key = 1
        value = [1, 2, 3]

        # Act & Assert
        with pytest.raises(ValueError):
            zones[key] = value  # type: ignore

    def test_default_values_for_id_and_name(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones sets default values for
        ADTPulseZoneData.id_ and name if not set when setting a Zone.
        """
        # Arrange
        zones = ADTPulseZones()

        # Act
        zones[1] = ADTPulseZoneData("", "")

        # Assert
        assert zones[1].id_ == "sensor-1"
        assert zones[1].name == "Sensor for Zone 1"

    def test_invalid_zone_data_in_flattening(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones raises a ValueError
        if there is invalid Zone data in ADTPulseZones when flattening.
        """
        # Arrange
        zones = ADTPulseZones()
        zones[1] = ADTPulseZoneData("Zone 1", "sensor-1")
        zones[2] = ADTPulseZoneData("Zone 2", "sensor-2")
        zones[3] = ADTPulseZoneData("Zone 3", "sensor-3")
        with pytest.raises(TypeCheckError):
            zones[3].tags = "Invalid Tags"  # type: ignore

    # ADTPulseZones skips incomplete zone data when updating zone attributes
    def test_skips_incomplete_zone_data(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones skips
        incomplete zone data when updating zone attributes.
        """
        # Arrange
        zones = ADTPulseZones()
        dev_attr = {
            "name": "Zone 1",
            "type_model": "Window Sensor",
            "zone": "1",
            "status": "Online",
        }

        # Act
        zones.update_zone_attributes(dev_attr)

        # Assert
        assert len(zones) == 1
        assert zones[1].name == "Zone 1"
        assert zones[1].id_ == "sensor-1"
        assert zones[1].tags == ADT_NAME_TO_DEFAULT_TAGS["Window"]
        assert zones[1].status == "Online"
        assert zones[1].state == "Unknown"
        assert zones[1].last_activity_timestamp == 0

    # ADTPulseZones can handle unknown sensor types when updating zone attributes
    def test_handle_unknown_sensor_types(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones can handle
        unknown sensor types when updating zone attributes.
        """
        # Arrange
        zones = ADTPulseZones()
        dev_attr = {
            "name": "Sensor 1",
            "type_model": "Unknown Sensor Type",
            "zone": "1",
            "status": "Online",
        }

        # Act
        zones.update_zone_attributes(dev_attr)

        # Assert
        assert len(zones) == 1
        assert zones[1].name == "Sensor 1"
        assert zones[1].id_ == "sensor-1"
        assert zones[1].tags == ("sensor", "doorWindow")
        assert zones[1].status == "Online"
        assert zones[1].state == "Unknown"
        assert zones[1].last_activity_timestamp == 0

    # ADTPulseZones can handle missing status when updating zone attributes
    def test_missing_status_handling_fixed(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones can handle missing status when updating zone attributes.
        """
        # Arrange
        zones = ADTPulseZones()
        dev_attr = {
            "name": "Zone 1",
            "type_model": "Window Sensor",
            "zone": "1",
            "status": "Unknown",  # Added status key with value "Unknown"
        }

        # Act
        zones.update_zone_attributes(dev_attr)

        # Assert
        assert len(zones) == 0

    # ADTPulseZones can handle invalid datetime when updating last activity timestamp
    def test_handle_invalid_datetime(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones can handle
        invalid datetime when updating last activity timestamp.
        """
        # Arrange
        zones = ADTPulseZones()
        zones[1] = ADTPulseZoneData("name", "id")
        key = 1
        invalid_dt = "2022-13-01 12:00:00"  # Invalid datetime format

        # Act
        with pytest.raises(ValueError):
            dt = datetime.strptime(invalid_dt, "%Y-%m-%d %H:%M:%S")
            zones.update_last_activity_timestamp(key, dt)

        # Assert
        assert zones[key].last_activity_timestamp == 0

    # ADTPulseZones can handle missing name when updating zone attributes
    def test_handle_missing_name_when_updating_zone_attributes(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones can handle missing name when updating zone attributes.
        """
        # Arrange
        zones = ADTPulseZones()
        dev_attr = {
            "name": "Unknown",
            "type_model": "Window Sensor",
            "zone": "1",
            "status": "Online",
        }

        # Act
        zones.update_zone_attributes(dev_attr)

        # Assert
        assert len(zones) == 0

    # ADTPulseZones can handle missing zone when updating zone attributes
    def test_handle_missing_zone(self):
        """
        ADTPulseZones test.

        Test that ADTPulseZones can handle missing zone when updating zone attributes.
        """
        # Arrange
        zones = ADTPulseZones()
        dev_attr = {
            "name": "Sensor 1",
            "type_model": "Window Sensor",
            "zone": "1",
            "status": "Online",
        }

        # Act
        zones.update_zone_attributes(dev_attr)

        # Assert
        assert len(zones) == 1
        assert zones[1].name == "Sensor 1"
        assert zones[1].id_ == "sensor-1"
        assert zones[1].tags == ADT_NAME_TO_DEFAULT_TAGS["Window"]
        assert zones[1].status == "Online"
        assert zones[1].state == "Unknown"
        assert zones[1].last_activity_timestamp == 0
