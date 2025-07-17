"""Unit tests for pyadtpulse exception classes and their behaviors."""

from time import time

import pytest

from pyadtpulse.exceptions import (
    PulseAccountLockedError,
    PulseAuthenticationError,
    PulseClientConnectionError,
    PulseConnectionError,
    PulseExceptionWithBackoff,
    PulseExceptionWithRetry,
    PulseLoginException,
    PulseNotLoggedInError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
)
from pyadtpulse.pulse_backoff import PulseBackoff


class TestCodeUnderTest:
    """PulseExceptionWithBackoff initialized with message and PulseBackoff object."""

    def test_pulse_exception_with_backoff_initialization(self):
        """
        Test PulseExceptionWithBackoff.

        can be initialized with a message and a PulseBackoff object
        """
        backoff = PulseBackoff("test", 1.0)
        exception = PulseExceptionWithBackoff("error", backoff)
        assert str(exception) == "PulseExceptionWithBackoff: error"
        assert exception.backoff == backoff
        assert backoff.backoff_count == 1

    def test_pulse_exception_with_backoff_increment(self):
        """Test PulseExceptionWithBackoff increments backoff count."""
        backoff = PulseBackoff("test", 1.0)
        PulseExceptionWithBackoff("error", backoff)
        assert backoff.backoff_count == 1

    def test_pulse_exception_with_retry_initialization(self):
        """
        Test PulseExceptionWithRetry.

        initialized with message, backoff, and retry time
        """
        backoff = PulseBackoff("test", 1.0)
        retry_time = time() + 10
        exception = PulseExceptionWithRetry("error", backoff, retry_time)
        assert str(exception) == "PulseExceptionWithRetry: error"
        assert exception.backoff == backoff
        assert exception.retry_time == retry_time

    def test_pulse_exception_with_retry_reset_and_set_absolute_backoff_time(self):
        """
        Test PulseExceptionWithRetry.

        resets backoff count and sets absolute backoff time
        """
        backoff = PulseBackoff("test", 1.0)
        backoff.increment_backoff()
        retry_time = time() + 10
        PulseExceptionWithRetry("error", backoff, retry_time)
        assert backoff.backoff_count == 0
        assert backoff.expiration_time == retry_time

    def test_pulse_server_connection_error_inheritance_fixed(self):
        """Test PulseServerConnectionError inheritance."""
        assert issubclass(PulseServerConnectionError, PulseExceptionWithBackoff)
        assert issubclass(PulseServerConnectionError, PulseConnectionError)

    def test_pulse_client_connection_error_inheritance_fixed(self):
        """Test PulseClientConnectionError inheritance."""
        assert issubclass(PulseClientConnectionError, PulseExceptionWithBackoff)
        assert issubclass(PulseClientConnectionError, PulseConnectionError)

    def test_pulse_exception_with_backoff_invalid_initialization(self):
        """Test PulseExceptionWithBackoff invalid initialization."""
        with pytest.raises(Exception):  # noqa: B017
            PulseExceptionWithBackoff(123, "backoff")  # type: ignore

    def test_pulse_exception_with_retry_invalid_initialization(self):
        """Test PulseExceptionWithRetry invalid initialization."""
        backoff = PulseBackoff("test", 1.0)
        with pytest.raises(Exception):  # noqa: B017
            PulseExceptionWithRetry(123, backoff, "retry")  # type: ignore
        with pytest.raises(Exception):  # noqa: B017
            PulseExceptionWithRetry("error", "backoff", time() + 10)  # type: ignore
        with pytest.raises(Exception):  # noqa: B017
            PulseExceptionWithRetry("error", backoff, "retry")  # type: ignore

    def test_pulse_exception_with_retry_past_retry_time(self):
        """Test PulseExceptionWithRetry with past retry time."""
        backoff = PulseBackoff("test", 1.0)
        backoff.increment_backoff()
        retry_time = time() - 10
        with pytest.raises(PulseExceptionWithRetry):
            raise PulseExceptionWithRetry(
                "retry must be in the future", backoff, retry_time
            )
        # 1 backoff for increment
        assert backoff.backoff_count == 2  # noqa: PLR2004
        assert backoff.expiration_time == 0.0

    def test_pulse_service_temporarily_unavailable_error_past_retry_time_fixed(self):
        """Test PulseServiceTemporarilyUnavailableError with past retry time."""
        backoff = PulseBackoff("test", 1.0)
        backoff.increment_backoff()
        retry_time = time() - 10
        with pytest.raises(PulseServiceTemporarilyUnavailableError):
            raise PulseServiceTemporarilyUnavailableError(backoff, retry_time)
        assert backoff.backoff_count == 2  # noqa: PLR2004
        assert backoff.expiration_time == 0.0

    def test_pulse_authentication_error_inheritance(self):
        """Test PulseAuthenticationError inheritance."""
        PulseBackoff("test", 1.0)
        exception = PulseAuthenticationError()
        assert isinstance(exception, PulseLoginException)

    def test_pulse_service_temporarily_unavailable_error(self):
        """Test PulseServiceTemporarilyUnavailableError inheritance."""
        backoff = PulseBackoff("test", 1.0)
        exception = PulseServiceTemporarilyUnavailableError(
            backoff, retry_time=time() + 10.0
        )
        assert backoff.backoff_count == 0
        assert isinstance(exception, PulseExceptionWithRetry)
        assert isinstance(exception, PulseConnectionError)

    def test_pulse_account_locked_error_inheritance(self):
        """Test PulseAccountLockedError inheritance."""
        backoff = PulseBackoff("test", 1.0)
        exception = PulseAccountLockedError(backoff, time() + 10.0)
        assert backoff.backoff_count == 0
        assert isinstance(exception, PulseExceptionWithRetry)
        assert isinstance(exception, PulseLoginException)

    def test_pulse_exception_with_backoff_string_representation(self):
        """Test PulseExceptionWithBackoff string representation."""
        backoff = PulseBackoff("test", 1.0)
        exception = PulseExceptionWithBackoff("error", backoff)
        assert str(exception) == "PulseExceptionWithBackoff: error"
        assert exception.backoff == backoff
        assert backoff.backoff_count == 1

    def test_pulse_exception_with_retry_string_representation_fixed(self):
        """Test PulseExceptionWithRetry string representation."""
        backoff = PulseBackoff("test", 1.0)
        exception = PulseExceptionWithRetry("error", backoff, time() + 10)
        expected_string = "PulseExceptionWithRetry: error"
        assert str(exception) == expected_string

    def test_pulse_not_logged_in_error_inheritance(self):
        """Test PulseNotLoggedInError inheritance."""
        PulseBackoff("test", 1.0)
        exception = PulseNotLoggedInError()
        assert isinstance(exception, PulseLoginException)

    def test_pulse_exception_with_retry_string_representation(self):
        """Test PulseExceptionWithRetry string representation."""
        backoff = PulseBackoff("test", 1.0)
        exception = PulseExceptionWithRetry("error", backoff, time() + 10)
        assert str(exception) == "PulseExceptionWithRetry: error"
        assert exception.backoff == backoff
        assert backoff.backoff_count == 0
