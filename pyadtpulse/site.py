"""Module representing an ADT Pulse Site."""

import re
import logging
from time import time
from asyncio import Task, gather, create_task
from datetime import datetime

from lxml import html
from typeguard import typechecked

from .util import make_etree, remove_prefix, parse_pulse_datetime
from .const import (
    ADT_DEVICE_URI,
    ADT_SYSTEM_URI,
    ADT_GATEWAY_URI,
    ADT_HISTORY_URI,
    ADT_GATEWAY_STRING,
)
from .exceptions import (
    PulseGatewayOfflineError,
    PulseClientConnectionError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
)
from .site_properties import ADTPulseSiteProperties
from .pulse_connection import PulseConnection

LOG = logging.getLogger(__name__)

SECURITY_PANEL_ID = "1"
SECURITY_PANEL_NAME = "Security Panel"

# Hours of history to read for zones the orb gave no last event time: a week
# (the longest period the history page offers) for the zones parsed at login,
# then the past hour for zones that change while we watch.
LOGIN_HISTORY_HOURS = 168
CHANGE_HISTORY_HOURS = 1
HISTORY_ZONE_RE = re.compile(r"\(Zone (\d+)\)")


def _parse_zone_history(tree: html.HtmlElement) -> dict[int, datetime]:
    """
    Find each zone's newest event on the portal's history page.

    Rows look like "Today 6:29 PM | Door Kitchen (Zone 4) set to Closed."

    Args:
        tree (html.HtmlElement): the parsed history page

    Returns:
        dict[int, datetime]: zone id to the time of its newest event

    """
    events: dict[int, datetime] = {}
    for row in tree.iterfind(".//table[@id='myTable']//tr"):
        stamp = row.find(".//span[@class='p_timestampText']")
        detail = row.find("td")
        if stamp is None or detail is None:
            continue
        match = HISTORY_ZONE_RE.search(detail.text_content())
        if match is None:
            continue
        try:
            when = parse_pulse_datetime(stamp.text_content())
        except ValueError:
            LOG.debug("Skipping history row with time %r", stamp.text_content())
            continue
        zone = int(match.group(1))
        if zone not in events or when > events[zone]:
            events[zone] = when
    return events


class ADTPulseSite(ADTPulseSiteProperties):
    """Represents an individual ADT Pulse site."""

    __slots__ = (
        "_pulse_connection",
        "_tripped_zones",
        "_trouble_zones",
        "_zones_without_activity",
    )

    @typechecked
    def __init__(self, pulse_connection: PulseConnection, site_id: str, name: str):
        """
        Initialize.

        Args:
            pulse_connection (PulseConnection): Pulse connection.
            site_id (str): Site ID.
            name (str): Site name.

        """
        self._pulse_connection = pulse_connection
        super().__init__(site_id, name)
        self._trouble_zones: set[int] | None = None
        self._tripped_zones: set[int] = set()
        # zones the orb updated without a last event time, mapped to the
        # hours of history to read for them
        self._zones_without_activity: dict[int, int] = {}

    @typechecked
    async def async_arm_home(self, force_arm: bool = False) -> bool:
        """Arm system home async."""
        return await self.alarm_control_panel.async_arm_home(
            self._pulse_connection, force_arm=force_arm
        )

    @typechecked
    async def async_arm_away(self, force_arm: bool = False) -> bool:
        """Arm system away async."""
        return await self.alarm_control_panel.async_arm_away(
            self._pulse_connection, force_arm=force_arm
        )

    @typechecked
    async def async_arm_night(self, force_arm: bool = False) -> bool:
        """Arm system away async."""
        return await self.alarm_control_panel.async_arm_night(
            self._pulse_connection, force_arm=force_arm
        )

    async def async_disarm(self) -> bool:
        """Disarm system async."""
        return await self.alarm_control_panel.async_disarm(self._pulse_connection)

        #        status_orb = summary_html_soup.find('canvas', {'id': 'ic_orb'})
        #        if status_orb:
        #            self._status = status_orb['orb']
        #            LOG.warning(status_orb)
        #            LOG.debug("Alarm status = %s", self._status)
        #        else:
        #            LOG.error("Failed to find alarm status in ADT summary!")

        # if we should also update the zone details, force a fresh fetch
        # of data from ADT Pulse

    async def _get_device_attributes(self, device_id: str) -> dict[str, str] | None:
        """
        Retrieve the attributes of a device.

        Args:
            device_id (str): The ID of the device to retrieve attributes for.

        Returns:
            Optional[dict[str, str]]: A dictionary of attribute names and their
                corresponding values,
                or None if the device response lxml tree is None.

        """
        result: dict[str, str] = {}
        if device_id == ADT_GATEWAY_STRING:
            device_response = await self._pulse_connection.async_query(
                ADT_GATEWAY_URI, timeout=10
            )
        else:
            device_response = await self._pulse_connection.async_query(
                ADT_DEVICE_URI, extra_params={"id": device_id}
            )
        device_response_etree = make_etree(
            device_response[0],
            device_response[1],
            device_response[2],
            logging.DEBUG,
            "Failed loading device attributes from ADT Pulse service",
        )
        if device_response_etree is None:
            return None
        for dev_info_row in device_response_etree.findall(
            path=".//td[@class='InputFieldDescriptionL']",
            namespaces=None,
        ):
            identity_text = (
                str(dev_info_row.text_content())
                .lower()
                .strip()
                .rstrip(":")
                .replace(" ", "_")
                .replace("/", "_")
            )
            sibling = dev_info_row.getnext()
            if sibling is None:
                value = "Unknown"
            else:
                value = str(sibling.text_content().strip())
            result.update({identity_text: value})
        return result

    @typechecked
    async def async_set_device(self, device_id: str) -> None:
        """
        Set the device attributes for the given device ID.

        Args:
            device_id (str): The ID of the device.

        """
        dev_attr = await self._get_device_attributes(device_id)
        if dev_attr is None:
            return
        if device_id == ADT_GATEWAY_STRING:
            self._gateway.set_gateway_attributes(dev_attr)
            return
        if device_id == SECURITY_PANEL_ID:
            self._alarm_panel.set_alarm_attributes(dev_attr)
            return
        if device_id.isdigit():
            self._zones.update_zone_attributes(dev_attr)
        else:
            LOG.debug("Zone %s is not an integer, skipping", device_id)

    @typechecked
    async def async_fetch_devices(self, tree: html.HtmlElement | None) -> bool:
        """
        Fetch the devices from the tree and update the zone attributes.

        Args:
            tree: (Optional[html.HtmlElement]): The lxml etree containing
                the devices.

        Returns:
            bool: True if the devices were fetched and zone attributes were updated
                successfully, False otherwise.

        """
        regex_device = r"goToUrl\('device.jsp\?id=(\d*)'\);"
        task_list: list[Task] = []
        zone_id: str | None = None

        def add_zone_from_row(row_tds: list[html.HtmlElement]) -> str | None:
            """
            Add a zone from an HtmlElement row.

            Returns None if successful, otherwise the zone ID if present.
            """
            zone_id: str | None = None
            if row_tds and len(row_tds) > 4:
                zone_name: str = row_tds[1].text_content().strip()
                zone_id = row_tds[2].text_content().strip()
                zone_type: str = row_tds[4].text_content().strip()
                zone_status = "Unknown"
                zs_temp = row_tds[0].find(
                    path="canvas",
                    namespaces=None,
                )
                if (
                    zs_temp is not None
                    and zs_temp.get("title") is not None
                    and zs_temp.get("title") != ""
                ):
                    zone_status = zs_temp.get("title")
                if (
                    zone_id is not None
                    and zone_id.isdecimal()
                    and zone_name
                    and zone_type
                ):
                    self._zones.update_zone_attributes(
                        {
                            "name": zone_name,
                            "zone": zone_id,
                            "type_model": zone_type,
                            "status": zone_status.strip(),
                        }
                    )
                    return None
            return zone_id

        def check_panel_or_gateway(
            regex_device: str,
            device_name: str,
            zone_id: str | None,
            on_click_value_text: str,
        ) -> Task | None:
            result = re.findall(regex_device, on_click_value_text)
            if result:
                device_id = result[0]
                if device_id == SECURITY_PANEL_ID or device_name == SECURITY_PANEL_NAME:
                    return create_task(self.async_set_device(device_id))
                if zone_id and zone_id.isdecimal():
                    return create_task(self.async_set_device(device_id))
            LOG.debug("Skipping %s as it doesn't have an ID", device_name)
            return None

        if tree is None:
            response = await self._pulse_connection.async_query(ADT_SYSTEM_URI)
            tree = make_etree(
                response[0],
                response[1],
                response[2],
                logging.WARNING,
                "Failed loading zone status from ADT Pulse service",
            )
            if tree is None:
                return False
        for row in tree.findall(
            path=".//tr[@class='p_listRow'][@onclick]",
            namespaces=None,
        ):
            tmp_device_name = row.find(".//a")
            if tmp_device_name is None:
                LOG.debug("Skipping device as it has no name")
                continue
            device_name = tmp_device_name.text_content().strip()
            row_tds = row.findall("td")
            zone_id = add_zone_from_row(row_tds)
            if zone_id is None:
                continue
            on_click_value_text = row.get("onclick")
            if on_click_value_text is None:
                LOG.debug("Skipping device %s as it has no onclick value", device_name)
                continue
            if (
                on_click_value_text in ("goToUrl('gateway.jsp');", "Gateway")
                or device_name == "Gateway"
            ):
                task_list.append(create_task(self.async_set_device(ADT_GATEWAY_STRING)))
            elif (
                result := check_panel_or_gateway(
                    regex_device,
                    device_name,
                    zone_id,
                    on_click_value_text,
                )
            ) is not None:
                task_list.append(result)

        await gather(*task_list)
        self._last_updated = int(time())
        return True

    def update_zone_from_etree(self, tree: html.HtmlElement) -> set[int]:  # noqa: PLR0912, PLR0915
        """
        Update the zone information based on the provided lxml etree.

        Args:
            tree:html.HtmlElement: the parsed response tree

        Returns:
            set[int]: a set of zone ids that were updated

        Raises:
            PulseGatewayOffline: If the gateway is offline.

        """

        def get_zone_id(zone_row: html.HtmlElement) -> int | None:
            try:
                zone = int(
                    remove_prefix(
                        zone_row.find(
                            path=".//div[@class='p_grayNormalText']",
                            namespaces=None,
                        ).text_content(),
                        "Zone",
                    )
                )
            except AttributeError:
                LOG.debug("skipping row due to no zone id")
                return None
            except ValueError:
                LOG.debug("skipping row due to zone not being an integer")
                return None
            return zone

        def get_zone_last_update(
            zone_row: html.HtmlElement, zone: int
        ) -> datetime | None:
            # Pulse 30 and later leave the title out; the time is then read
            # from the history page by async_update_zone_activity
            icon = zone_row.find(path=".//span[@class='devStatIcon']", namespaces=None)
            title = icon.get("title") if icon is not None else None
            if not title:
                return None
            try:
                return parse_pulse_datetime(remove_prefix(title, "Last Event:"))
            except ValueError:
                LOG.debug("Unable to parse last event time %r for zone %d", title, zone)
                return None

        def get_zone_state(zone_row: html.HtmlElement, zone: int) -> str:
            try:
                state = remove_prefix(
                    zone_row.find(
                        path=".//canvas[@class='p_ic_icon_device']",
                        namespaces=None,
                    ).get("icon"),
                    "devStat",
                )
            except (AttributeError, ValueError):
                LOG.debug("Unable to set state for zone %d due to malformed html", zone)
                return "Unknown"
            return state

        def get_zone_status(zone_row: html.HtmlElement, zone: int) -> str:
            try:
                status = (
                    zone_row.find(
                        path=".//td[@class='p_listRow']",
                        namespaces=None,
                    )
                    .getnext()
                    .text_content()
                )
                status = status.replace("\xa0", "")
                if status.startswith("Trouble"):
                    trouble_code = status.split()
                    if len(trouble_code) > 1:
                        status = " ".join(trouble_code[1:])
                    else:
                        status = "Unknown trouble code"
                else:
                    status = "Online"
            except (ValueError, AttributeError):
                LOG.debug(
                    "Unable to set status for zone %s because html malformed", zone
                )
                status = "Unknown"
            return status

        def update_zone_from_row(
            zone: int,
            state: str,
            status: str,
            last_update: datetime | None,
            history_hours: int,
        ) -> None:
            # id:    [integer]
            # name:  device name
            # tags:  sensor,[doorWindow,motion,glass,co,fire]
            # timestamp: timestamp of last activity
            # state: OK (device okay)
            #        Open (door/window opened)
            #        Motion (detected motion)
            #        Tamper (glass broken or device tamper)
            #        Alarm (detected CO/Smoke)
            #        Unknown (device offline)

            # update device state from ORB info
            if not self._zones:
                LOG.warning("No zones exist")
                return
            if last_update is None:
                # keep the time we had until the history page says otherwise
                previous = self._zones[zone].last_activity_timestamp
                self._zones.update_device_info(zone, state, status)
                self._zones[zone].last_activity_timestamp = previous
                self._zones_without_activity[zone] = max(
                    history_hours, self._zones_without_activity.get(zone, 0)
                )
            else:
                self._zones.update_device_info(zone, state, status, last_update)
                self._zones_without_activity.pop(zone, None)
            LOG.debug(
                "Set zone %d - to %s, status %s with timestamp %s",
                zone,
                state,
                status,
                last_update,
            )
            retval.add(zone)

        retval: set[int] = set()
        start_time = 0.0
        if self._pulse_connection.detailed_debug_logging:
            start_time = time()
        # parse ADT's convulated html to get sensor status
        try:
            orb_status = tree.find(
                path=".//canvas[@id='ic_orb']",
                namespaces=None,
            ).get("orb")
            if orb_status == "offline":
                self.gateway.is_online = False
                raise PulseGatewayOfflineError(self.gateway.backoff)
            else:
                self.gateway.is_online = True
                self.gateway.backoff.reset_backoff()

        except (AttributeError, ValueError):
            LOG.error("Failed to retrieve alarm status from orb!")
        first_pass = False
        if self._trouble_zones is None:
            first_pass = True
            self._trouble_zones = set()
        original_non_default_zones = self._trouble_zones | self._tripped_zones
        history_hours = LOGIN_HISTORY_HOURS if first_pass else CHANGE_HISTORY_HOURS
        # v26 and lower: temp = row.find("span", {"class": "p_grayNormalText"})
        for row in tree.findall(
            path=".//tr[@class='p_listRow']",
            namespaces=None,
        ):
            zone_id = get_zone_id(row)
            if not zone_id:
                continue
            status = get_zone_status(row, zone_id)
            state = get_zone_state(row, zone_id)
            last_update = get_zone_last_update(row, zone_id)
            # we know that orb sorts with trouble first, tripped next, then ok
            if status != "Online":
                self._trouble_zones.add(zone_id)
                self._tripped_zones.discard(zone_id)
                update_zone_from_row(zone_id, state, status, last_update, history_hours)
                continue
            # this should be trouble or OK sensors
            if state != "OK":
                self._tripped_zones.add(zone_id)
                if zone_id in self._trouble_zones:
                    self._trouble_zones.remove(zone_id)
                update_zone_from_row(zone_id, state, status, last_update, history_hours)
                continue
            # everything here is OK, so we just need to check if
            #   anything in tripped or trouble states have
            # returned to normal
            if first_pass:
                update_zone_from_row(zone_id, state, status, last_update, history_hours)
                continue
            if not original_non_default_zones:
                break
            if zone_id in original_non_default_zones:
                update_zone_from_row(zone_id, state, status, last_update, history_hours)
                original_non_default_zones.remove(zone_id)
                if not original_non_default_zones:
                    break
                continue

        self._last_updated = int(time())

        if self._pulse_connection.detailed_debug_logging:
            LOG.debug("Updated zones in %f seconds", time() - start_time)
        return retval

    async def async_update_zone_activity(self) -> set[int]:
        """
        Read last activity times the orb left out from the history page.

        Pulse 30 and later no longer put each zone's last event time in the
        orb, so update_zone_from_etree leaves those zones' times as they were.
        This fetches the history page once, for the past week if any of them
        were parsed at login and the past hour otherwise, and sets each zone's
        time to its newest event there. Zones with no event in that period
        keep their time. If the page can't be fetched, the zones wait for the
        next call.

        Returns:
            set[int]: the zones whose last activity time changed

        """
        if not self._zones_without_activity:
            return set()
        hours = max(self._zones_without_activity.values())
        try:
            code, text, url = await self._pulse_connection.async_query(
                ADT_HISTORY_URI,
                extra_params={"filter": "All", "timefilter": str(hours)},
            )
        except (
            PulseClientConnectionError,
            PulseServerConnectionError,
            PulseServiceTemporarilyUnavailableError,
        ) as ex:
            LOG.warning("Could not fetch zone history from ADT Pulse: %s", ex)
            return set()
        tree = make_etree(
            code,
            text,
            url,
            logging.WARNING,
            "Failed loading zone history from ADT Pulse service",
        )
        if tree is None:
            return set()
        events = _parse_zone_history(tree)
        updated: set[int] = set()
        for zone in self._zones_without_activity:
            when = events.get(zone)
            if when is None or zone not in self._zones:
                continue
            timestamp = int(when.timestamp())
            if self._zones[zone].last_activity_timestamp != timestamp:
                self._zones[zone].last_activity_timestamp = timestamp
                updated.add(zone)
        LOG.debug(
            "Set last activity for zones %s from %d hours of history",
            sorted(updated),
            hours,
        )
        self._zones_without_activity.clear()
        return updated
