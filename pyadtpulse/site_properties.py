"""Pulse Site Properties."""

from typeguard import typechecked

from .zones import ADTPulseZones, ADTPulseFlattenedZone
from .gateway import ADTPulseGateway
from .alarm_panel import ADTPulseAlarmPanel


class ADTPulseSiteProperties:
    """Pulse Site Properties."""

    __slots__ = (
        "_alarm_panel",
        "_gateway",
        "_id",
        "_last_updated",
        "_name",
        "_zones",
    )

    @typechecked
    def __init__(self, site_id: str, name: str):
        """Init for ADTPulseSiteProperties."""
        self._id = site_id
        self._name = name
        self._last_updated: int = 0
        self._zones = ADTPulseZones()
        self._alarm_panel = ADTPulseAlarmPanel()
        self._gateway = ADTPulseGateway()

    @property
    def id(self) -> str:
        """
        Get site id.

        Returns:
            str: the site id

        """
        return self._id

    @property
    def name(self) -> str:
        """
        Get site name.

        Returns:
            str: the site name

        """
        return self._name

    # FIXME: should this actually return if the alarm is going off!?  How do we
    # return state that shows the site is compromised??

    @property
    def last_updated(self) -> int:
        """
        Return time site last updated.

        Returns:
            int: the time site last updated as datetime

        """
        return self._last_updated

    @property
    def zones(self) -> list[ADTPulseFlattenedZone]:
        """
        Return all zones registered with the ADT Pulse account.

        Returns:
            list[ADTPulseFlattenedZone]: the cached zones from the last fetch,
                empty if the site has none

        """
        return self._zones.flatten()

    @property
    def zones_as_dict(self) -> ADTPulseZones:
        """
        Return zone information in dictionary form.

        Returns:
            ADTPulseZones: all zone information, empty if the site has none

        """
        return self._zones

    @property
    def alarm_control_panel(self) -> ADTPulseAlarmPanel:
        """
        Return the alarm panel object for the site.

        Returns:
            Optional[ADTPulseAlarmPanel]: the alarm panel object

        """
        return self._alarm_panel

    @property
    def gateway(self) -> ADTPulseGateway:
        """
        Get gateway device object.

        Returns:
            ADTPulseGateway: Gateway device

        """
        return self._gateway
