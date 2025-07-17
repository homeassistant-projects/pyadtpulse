"""Unit tests for the PulseAuthenticationProperties class in the pyadtpulse package."""

import pytest
import typeguard
from typeguard import TypeCheckError

from pyadtpulse.pulse_authentication_properties import PulseAuthenticationProperties


class TestPulseAuthenticationProperties:
    """Unit tests for the PulseAuthenticationProperties class."""

    def test_initialize_with_valid_credentials(self):
        """
        PulseAuthenticationProperties test.

        Test initializing PulseAuthenticationProperties with
        valid username, password, and fingerprint.
        """
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"

        # Act
        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Assert
        assert properties.username == username
        assert properties.password == password
        assert properties.fingerprint == fingerprint

    def test_get_and_set_properties(self):
        """
        Get_and_set_properties test.

        Test getting and setting:
            username, password, fingerprint, site_id, and last_login_time properties.
        """
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"
        site_id = "site123"
        last_login_time = 123456789

        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Act
        properties.username = "new_username@example.com"
        properties.password = "new_password"
        properties.fingerprint = "new_fingerprint"
        properties.site_id = site_id
        properties.last_login_time = last_login_time

        # Assert
        assert properties.username == "new_username@example.com"
        assert properties.password == "new_password"
        assert properties.fingerprint == "new_fingerprint"
        assert properties.site_id == site_id
        assert properties.last_login_time == last_login_time

    # Get last_login_time property after setting it
    def test_get_last_login_time_after_setting(self):
        """Test getting last_login_time property after setting it."""
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"
        last_login_time = 123456789

        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Act
        properties.last_login_time = last_login_time

        # Assert
        assert properties.last_login_time == last_login_time

    # Set username, password, fingerprint, site_id properties with valid values
    def test_set_properties_with_valid_values(self):
        """
        Set_properties_with_valid_values test.

        Test setting:
            username, password, fingerprint, site_id properties with valid values.
        """
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"
        site_id = "site123"

        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Act
        properties.site_id = site_id

        # Assert
        assert properties.username == username
        assert properties.password == password
        assert properties.fingerprint == fingerprint
        assert properties.site_id == site_id

    def test_set_properties_with_non_empty_fingerprint(self):
        """
        Set_properties_with_non_empty_fingerprint test.

        Test setting:
            username, password, fingerprint properties with non-empty fingerprint.
        """
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"

        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Act
        properties.username = username
        properties.password = password
        properties.fingerprint = fingerprint

        # Assert
        assert properties.username == username
        assert properties.password == password
        assert properties.fingerprint == fingerprint

    # Set site_id property with empty string
    def test_set_site_id_with_empty_string(self):
        """Test setting site_id property with empty string."""
        # Arrange
        site_id = ""

        properties = PulseAuthenticationProperties(
            "test@example.com", "password123", "fingerprint123"
        )

        # Act
        properties.site_id = site_id

        # Assert
        assert properties.site_id == site_id

    # Initialize object with empty username, password, or fingerprint
    def test_initialize_with_empty_credentials(self):
        """
        Initialize_with_empty_credentials test.

        Test initializing PulseAuthenticationProperties with empty:
            username, password, or fingerprint.
        """
        # Arrange
        username = ""
        password = ""
        fingerprint = ""

        # Act and Assert
        with pytest.raises(ValueError):
            PulseAuthenticationProperties(username, password, fingerprint)

    # Initialize object with invalid username or password
    def test_initialize_with_invalid_credentials1(self):
        """
        Initialize_with_invalid_credentials1 test.

        Test initializing PulseAuthenticationProperties with invalid username/password.
        """
        # Arrange
        username = "invalid_username"
        password = "invalid_password"
        fingerprint = "fingerprint123"

        # Act and Assert
        with pytest.raises(ValueError):
            PulseAuthenticationProperties(username, password, fingerprint)

    # Set username, password, fingerprint properties with invalid values
    def test_set_properties_with_invalid_values(self):
        """Test setting username/password/fingerprint properties with invalid values."""
        # Arrange
        username = "invalid_username"
        password = ""
        fingerprint = ""

        properties = PulseAuthenticationProperties(
            "test@example.com", "password123", "fingerprint123"
        )

        # Act and Assert
        with pytest.raises(ValueError):
            properties.username = username

        with pytest.raises(ValueError):
            properties.password = password

        with pytest.raises(ValueError):
            properties.fingerprint = fingerprint

    # Set last_login_time property with non-integer value
    def test_set_last_login_time_with_non_integer_value(self):
        """Test setting last_login_time property with non-integer value."""
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"
        last_login_time = "invalid_time"  # Non-integer value

        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Act and Assert
        with pytest.raises(TypeCheckError) as exc_info:
            properties.last_login_time = last_login_time  # type: ignore

        # Assert
        assert (
            str(exc_info.value)
            == 'argument "login_time" (str) is not an instance of int'
        )

    # Set site_id property with non-string value
    def test_set_site_id_with_non_string_value(self):
        """Test setting site_id property with non-string value."""
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"
        site_id = 12345  # Non-string value

        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Act
        with pytest.raises(TypeCheckError):
            properties.site_id = site_id  # type: ignore

        # Assert
        assert not properties.site_id

    # Set last_login_time property with integer value
    def test_set_last_login_time_with_integer_value(self):
        """Test setting last_login_time property with integer value."""
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"
        last_login_time = 123456789

        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Act
        properties.last_login_time = last_login_time

        # Assert
        assert properties.last_login_time == last_login_time

    # Raise ValueError when initializing object with invalid username or password
    def test_initialize_with_invalid_credentials(self):
        """Test PulseAuthenticationProperties with invalid username or password."""
        # Arrange
        username = "invalid_username"
        password = ""
        fingerprint = "valid_fingerprint"

        # Act and Assert
        with pytest.raises(ValueError):
            PulseAuthenticationProperties(username, password, fingerprint)

    # Raise TypeError when setting site_id property with non-string value
    def test_raise_type_error_when_setting_site_id_with_non_string_value(self):
        """Test that TypeError is raised when setting site_id to a non-string value."""
        # Arrange
        properties = PulseAuthenticationProperties(
            "test@example.com", "password123", "fingerprint123"
        )

        # Act and Assert
        with pytest.raises(TypeCheckError):
            properties.site_id = 123  # type: ignore

    def test_invalid_properties(self):
        """
        Invalid_properties test.

        Test that ValueError is raised when setting invalid:
            username, password, and fingerprint properties.
        """
        # Arrange
        username = "test@example.com"
        password = "password123"
        fingerprint = "fingerprint123"
        properties = PulseAuthenticationProperties(username, password, fingerprint)

        # Act and Assert
        with pytest.raises(ValueError):
            properties.username = ""
        with pytest.raises(ValueError):
            properties.password = ""
        with pytest.raises(ValueError):
            properties.fingerprint = ""

    # Raise TypeCheckError when setting last_login_time property with non-integer value
    def test_raise_type_check_error_when_setting_last_login_time_with_non_integer_value(
        self,
    ):
        """
        TypeCheckError test.

        Test that a TypeCheckError is raised when
        setting the last_login_time property with a non-integer value.
        """
        # Arrange
        properties = PulseAuthenticationProperties(
            "test@example.com", "password123", "fingerprint123"
        )

        # Act and Assert
        with pytest.raises(typeguard.TypeCheckError):
            properties.last_login_time = "invalid_time"  # type: ignore
