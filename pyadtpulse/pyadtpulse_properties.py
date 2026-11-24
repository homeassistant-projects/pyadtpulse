"""PyADTPulse Properties."""

import asyncio
import logging

from typeguard import typechecked

from .const import (
    ADT_MIN_RELOGIN_INTERVAL,
    ADT_MAX_KEEPALIVE_INTERVAL,
    ADT_DEFAULT_RELOGIN_INTERVAL,
    ADT_DEFAULT_KEEPALIVE_INTERVAL,
)

LOG = logging.getLogger(__name__)


class PyADTPulseProperties:
    """PyADTPulse Properties."""

    __slots__ = (
        "_keepalive_interval",
        "_relogin_interval",
        "_updates_exist",
    )

    @staticmethod
    @typechecked
    def _check_keepalive_interval(keepalive_interval: int) -> None:
        if keepalive_interval > ADT_MAX_KEEPALIVE_INTERVAL or keepalive_interval <= 0:
            raise ValueError(
                f"keepalive interval ({keepalive_interval}) must be "
                f"between 1 and {ADT_MAX_KEEPALIVE_INTERVAL}"
            )

    @staticmethod
    @typechecked
    def _check_relogin_interval(relogin_interval: int) -> None:
        # 0 disables relogin
        if relogin_interval != 0 and relogin_interval < ADT_MIN_RELOGIN_INTERVAL:
            raise ValueError(
                f"relogin interval ({relogin_interval}) must be 0 (disabled) "
                f"or at least {ADT_MIN_RELOGIN_INTERVAL}"
            )

    @typechecked
    def __init__(
        self,
        keepalive_interval: int = ADT_DEFAULT_KEEPALIVE_INTERVAL,
        relogin_interval: int = ADT_DEFAULT_RELOGIN_INTERVAL,
    ) -> None:
        """
        Create a PyADTPulse properties object.

        Args:
        keepalive_interval: (int):
        relogin_interval: (int):

        """
        # FIXME use thread event/condition, regular condition?
        # defer initialization to make sure we have an event loop

        self._updates_exist = asyncio.locks.Event()

        self.keepalive_interval = keepalive_interval
        self.relogin_interval = relogin_interval

    @property
    def relogin_interval(self) -> int:
        """
        Get re-login interval.

        Returns:
            int: number of minutes to re-login to Pulse
                 0 means disabled

        """
        return self._relogin_interval

    @relogin_interval.setter
    @typechecked
    def relogin_interval(self, interval: int | None) -> None:
        """
        Set re-login interval.

        Args:
            interval (int|None): The number of minutes between logins.
                            0 disables relogin.
                            If set to None, resets to ADT_DEFAULT_RELOGIN_INTERVAL

        Raises:
            ValueError: if a relogin interval other than 0 and less than
                        ADT_MIN_RELOGIN_INTERVAL minutes is specified

        """
        if interval is None:
            interval = ADT_DEFAULT_RELOGIN_INTERVAL
        else:
            self._check_relogin_interval(interval)
        self._relogin_interval = interval
        LOG.debug("relogin interval set to %d", self._relogin_interval)

    @property
    def keepalive_interval(self) -> int:
        """
        Get the keepalive interval in minutes.

        Returns:
            int: the keepalive interval

        """
        return self._keepalive_interval

    @keepalive_interval.setter
    @typechecked
    def keepalive_interval(self, interval: int | None) -> None:
        """
        Set the keepalive interval in minutes.

        Args:
            interval (int|None): The number of minutes between keepalive calls
                If set to None, resets to ADT_DEFAULT_KEEPALIVE_INTERVAL

        Raises:
            ValueError:
                if a keepalive interval of greater than
                ADT_MAX_KEEPALIVE_INTERVAL minutes is specified

        """
        if interval is None:
            interval = ADT_DEFAULT_KEEPALIVE_INTERVAL
        else:
            self._check_keepalive_interval(interval)
        self._keepalive_interval = interval
        LOG.debug("keepalive interval set to %d", self._keepalive_interval)

    @property
    def updates_exist(self) -> asyncio.locks.Event:
        """Check if updates exist."""
        return self._updates_exist
