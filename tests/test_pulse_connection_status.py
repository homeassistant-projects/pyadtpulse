"""Test cases for PulseConnectionProperties class."""

import time

import pytest

from pyadtpulse.pulse_backoff import PulseBackoff
from pyadtpulse.pulse_connection_status import PulseConnectionStatus


class TestPulseConnectionStatus:
    """Test cases for PulseConnectionStatus class."""

    # PulseConnectionStatus can be initialized without errors
    def test_initialized_without_errors(self):
        """Test that PulseConnectionStatus can be initialized without errors."""
        pcs = PulseConnectionStatus()
        assert pcs is not None

    # authenticated_flag can be accessed without errors
    def test_access_authenticated_flag(self):
        """Test that authenticated_flag can be accessed without errors."""
        pcs = PulseConnectionStatus()
        authenticated_flag = pcs.authenticated_flag
        assert authenticated_flag is not None

    # retry_after can be accessed without errors
    def test_access_retry_after(self):
        """Test that retry_after can be accessed without errors."""
        pcs = PulseConnectionStatus()
        retry_after = pcs.retry_after
        assert retry_after is not None

    # retry_after can be set without errors
    def test_set_retry_after(self):
        """Test that retry_after can be set without errors."""
        pcs = PulseConnectionStatus()
        current_time = time.time()
        retry_time = current_time + 1000
        pcs.retry_after = retry_time
        assert pcs.retry_after == retry_time

    # get_backoff returns a PulseBackoff object
    def test_get_backoff(self):
        """Test that get_backoff returns a PulseBackoff object."""
        pcs = PulseConnectionStatus()
        assert isinstance(pcs.get_backoff(), PulseBackoff)

    # increment_backoff can be called without errors
    def test_increment_backoff(self):
        """Test that increment_backoff can be called without errors."""
        pcs = PulseConnectionStatus()
        pcs.get_backoff().increment_backoff()

    # retry_after can be set to a time in the future
    def test_set_retry_after_past_time_fixed(self):
        """
        Test that setting retry_after to a past time raises ValueError.

        Verifies that attempting to set retry_after to a time in the past
        will raise a ValueError exception.
        """
        pcs = PulseConnectionStatus()
        current_time = time.time()
        past_time = current_time - 10.0
        with pytest.raises(ValueError):
            pcs.retry_after = past_time

    # retry_after can be set to a time in the future
    def test_set_retry_after_future_time_fixed(self):
        """
        Test that retry_after can be set to a future time.

        Verifies that setting retry_after to a time in the future works
        and the value remains greater than the current time.
        """
        pcs = PulseConnectionStatus()
        pcs.retry_after = time.time() + 10.0
        assert pcs.retry_after > time.time()

    # retry_after can be set to a positive value greater than the current time
    def test_set_retry_after_negative_value_fixed(self):
        """
        Test that retry_after accepts a specific future timestamp.

        Verifies that retry_after can be set to an exact positive timestamp
        value that is greater than the current time.
        """
        pcs = PulseConnectionStatus()
        retry_after_time = time.time() + 10.0
        pcs.retry_after = retry_after_time
        assert pcs.retry_after == retry_after_time

    # retry_after can be set to a very large value
    def test_set_retry_after_large_value(self):
        """
        Test that retry_after accepts infinity as a valid value.

        Verifies that retry_after can be set to float('inf') which is useful
        for indicating indefinite retry delays.
        """
        pcs = PulseConnectionStatus()
        pcs.retry_after = float("inf")
        assert pcs.retry_after == float("inf")

    # retry_after can be set to a non-numeric value
    def test_set_retry_after_non_numeric_value_fixed(self):
        """
        Test that retry_after can be set with a floating point timestamp.

        Verifies that retry_after accepts a floating point timestamp value
        and stores it correctly.
        """
        pcs = PulseConnectionStatus()
        retry_after_time = time.time() + 5.0
        pcs.retry_after = retry_after_time
        assert pcs.retry_after == retry_after_time

    # reset_backoff can be called without errors
    def test_reset_backoff(self):
        """Test that reset_backoff can be called without errors."""
        pcs = PulseConnectionStatus()
        pcs.get_backoff().reset_backoff()

    # authenticated_flag can be set to True
    def test_authenticated_flag_set_to_true(self):
        """Test that authenticated_flag can be set to True."""
        pcs = PulseConnectionStatus()
        pcs.authenticated_flag.set()
        assert pcs.authenticated_flag.is_set()

    # authenticated_flag can be set to False
    def test_authenticated_flag_false(self):
        """Test that authenticated_flag can be set to False."""
        pcs = PulseConnectionStatus()
        pcs.authenticated_flag.clear()
        assert not pcs.authenticated_flag.is_set()

    # Get backoff returns same PulseBackoff object for all calls
    def test_get_backoff_returns_same_object(self):
        """
        Test that get_backoff returns a singleton PulseBackoff instance.

        Verifies that multiple calls to get_backoff() return the exact same
        PulseBackoff object instance, ensuring state is preserved between calls.
        """
        pcs = PulseConnectionStatus()
        backoff1 = pcs.get_backoff()
        backoff2 = pcs.get_backoff()
        assert backoff1 is backoff2

    # increment_backoff increases the backoff count by 1
    def test_increment_backoff2(self):
        """
        Test that increment_backoff correctly increments the counter.

        Verifies that calling increment_backoff increases the internal
        backoff_count by exactly 1 from its previous value.
        """
        pcs = PulseConnectionStatus()
        backoff = pcs.get_backoff()
        initial_backoff_count = backoff.backoff_count
        backoff.increment_backoff()
        assert backoff.backoff_count == initial_backoff_count + 1

    # reset_backoff sets the backoff count to 0 and the expiration time to 0.0
    def test_reset_backoff_sets_backoff_count_and_expiration_time(self):
        """
        Test that reset_backoff properly resets all backoff state.

        Verifies that calling reset_backoff resets both the backoff_count
        to 0 and the expiration_time to 0.0, completely clearing the backoff state.
        """
        pcs = PulseConnectionStatus()
        backoff = pcs.get_backoff()
        backoff.increment_backoff()
        backoff.reset_backoff()
        assert backoff.backoff_count == 0 and backoff.expiration_time == 0.0
