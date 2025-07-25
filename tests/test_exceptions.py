# Generated by CodiumAI
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
    # PulseExceptionWithBackoff can be initialized with a message and a PulseBackoff object
    def test_pulse_exception_with_backoff_initialization(self):
        backoff = PulseBackoff("test", 1.0)
        exception = PulseExceptionWithBackoff("error", backoff)
        assert str(exception) == "PulseExceptionWithBackoff: error"
        assert exception.backoff == backoff
        assert backoff.backoff_count == 1

    # PulseExceptionWithBackoff increments the backoff count when initialized
    def test_pulse_exception_with_backoff_increment(self):
        backoff = PulseBackoff("test", 1.0)
        PulseExceptionWithBackoff("error", backoff)
        assert backoff.backoff_count == 1

    # PulseExceptionWithRetry can be initialized with a message, a PulseBackoff object, and a retry time
    def test_pulse_exception_with_retry_initialization(self):
        backoff = PulseBackoff("test", 1.0)
        retry_time = time() + 10
        exception = PulseExceptionWithRetry("error", backoff, retry_time)
        assert str(exception) == "PulseExceptionWithRetry: error"
        assert exception.backoff == backoff
        assert exception.retry_time == retry_time

    # PulseExceptionWithRetry resets the backoff count and sets an absolute backoff time if retry time is in the future
    def test_pulse_exception_with_retry_reset_and_set_absolute_backoff_time(self):
        backoff = PulseBackoff("test", 1.0)
        backoff.increment_backoff()
        retry_time = time() + 10
        PulseExceptionWithRetry("error", backoff, retry_time)
        assert backoff.backoff_count == 0
        assert backoff.expiration_time == retry_time

    # PulseServerConnectionError is a subclass of PulseExceptionWithBackoff and PulseConnectionError
    def test_pulse_server_connection_error_inheritance_fixed(self):
        assert issubclass(PulseServerConnectionError, PulseExceptionWithBackoff)
        assert issubclass(PulseServerConnectionError, PulseConnectionError)

    # PulseClientConnectionError is a subclass of PulseExceptionWithBackoff and PulseConnectionError
    def test_pulse_client_connection_error_inheritance_fixed(self):
        assert issubclass(PulseClientConnectionError, PulseExceptionWithBackoff)
        assert issubclass(PulseClientConnectionError, PulseConnectionError)

    # PulseExceptionWithBackoff raises an exception if initialized with an invalid message or non-PulseBackoff object
    def test_pulse_exception_with_backoff_invalid_initialization(self):
        with pytest.raises(Exception):
            PulseExceptionWithBackoff(123, "backoff")

    # PulseExceptionWithRetry raises an exception if initialized with an invalid message, non-PulseBackoff object, or invalid retry time
    def test_pulse_exception_with_retry_invalid_initialization(self):
        backoff = PulseBackoff("test", 1.0)
        with pytest.raises(Exception):
            PulseExceptionWithRetry(123, backoff, "retry")
        with pytest.raises(Exception):
            PulseExceptionWithRetry("error", "backoff", time() + 10)
        with pytest.raises(Exception):
            PulseExceptionWithRetry("error", backoff, "retry")

    # PulseExceptionWithRetry does not reset the backoff count or set an absolute backoff time if retry time is in the past
    def test_pulse_exception_with_retry_past_retry_time(self):
        backoff = PulseBackoff("test", 1.0)
        backoff.increment_backoff()
        retry_time = time() - 10
        with pytest.raises(PulseExceptionWithRetry):
            raise PulseExceptionWithRetry(
                "retry must be in the future", backoff, retry_time
            )
        # 1 backoff for increment
        assert backoff.backoff_count == 2
        assert backoff.expiration_time == 0.0

    # PulseServiceTemporarilyUnavailableError does not reset the backoff count or set an absolute backoff time if retry time is in the past
    def test_pulse_service_temporarily_unavailable_error_past_retry_time_fixed(self):
        backoff = PulseBackoff("test", 1.0)
        backoff.increment_backoff()
        retry_time = time() - 10
        with pytest.raises(PulseServiceTemporarilyUnavailableError):
            raise PulseServiceTemporarilyUnavailableError(backoff, retry_time)
        assert backoff.backoff_count == 2
        assert backoff.expiration_time == 0.0

    # PulseAuthenticationError is a subclass of PulseLoginException
    def test_pulse_authentication_error_inheritance(self):
        PulseBackoff("test", 1.0)
        exception = PulseAuthenticationError()
        assert isinstance(exception, PulseLoginException)

    # PulseServiceTemporarilyUnavailableError is a subclass of PulseExceptionWithRetry and PulseConnectionError
    def test_pulse_service_temporarily_unavailable_error(self):
        backoff = PulseBackoff("test", 1.0)
        exception = PulseServiceTemporarilyUnavailableError(
            backoff, retry_time=time() + 10.0
        )
        assert backoff.backoff_count == 0
        assert isinstance(exception, PulseExceptionWithRetry)
        assert isinstance(exception, PulseConnectionError)

    # PulseAccountLockedError is a subclass of PulseExceptionWithRetry and PulseLoginException
    def test_pulse_account_locked_error_inheritance(self):
        backoff = PulseBackoff("test", 1.0)
        exception = PulseAccountLockedError(backoff, time() + 10.0)
        assert backoff.backoff_count == 0
        assert isinstance(exception, PulseExceptionWithRetry)
        assert isinstance(exception, PulseLoginException)

    # PulseExceptionWithBackoff string representation includes the class name and message
    def test_pulse_exception_with_backoff_string_representation(self):
        backoff = PulseBackoff("test", 1.0)
        exception = PulseExceptionWithBackoff("error", backoff)
        assert str(exception) == "PulseExceptionWithBackoff: error"
        assert exception.backoff == backoff
        assert backoff.backoff_count == 1

    # PulseExceptionWithRetry string representation includes the class name, message, backoff object, and retry time
    def test_pulse_exception_with_retry_string_representation_fixed(self):
        backoff = PulseBackoff("test", 1.0)
        exception = PulseExceptionWithRetry("error", backoff, time() + 10)
        expected_string = "PulseExceptionWithRetry: error"
        assert str(exception) == expected_string

    # PulseNotLoggedInError is a subclass of PulseLoginException
    def test_pulse_not_logged_in_error_inheritance(self):
        PulseBackoff("test", 1.0)
        exception = PulseNotLoggedInError()
        assert isinstance(exception, PulseLoginException)

    # PulseExceptionWithRetry string representation does not include the backoff count if retry time is set
    def test_pulse_exception_with_retry_string_representation(self):
        backoff = PulseBackoff("test", 1.0)
        exception = PulseExceptionWithRetry("error", backoff, time() + 10)
        assert str(exception) == "PulseExceptionWithRetry: error"
        assert exception.backoff == backoff
        assert backoff.backoff_count == 0
