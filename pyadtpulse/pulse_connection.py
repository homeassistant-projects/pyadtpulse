"""
ADT Pulse connection. End users should probably not call this directly.

This is the main interface to the http functions to access ADT Pulse.
"""

import re
import json
import asyncio
import logging
import secrets
from http import HTTPStatus
from time import time
from asyncio import AbstractEventLoop
from urllib.parse import quote

from lxml import html
from yarl import URL
from aiohttp import ClientError, ClientTimeout
from typeguard import typechecked

from .util import make_etree, set_debug_lock
from .const import (
    ADT_LOGIN_URI,
    ADT_LOGOUT_URI,
    ADT_SUMMARY_URI,
    ADT_MFA_FAIL_URI,
    ADT_DEFAULT_LOGIN_TIMEOUT,
)
from .pulse_mfa import (
    ADT_MFA_STATE_HREF,
    ADT_POST_SIGNIN_URI,
    PulseMFAChallenge,
    mask_mfa_secrets,
)
from .exceptions import (
    PulseConnectionError,
    PulseMFARequiredError,
    PulseNotLoggedInError,
    PulseAccountLockedError,
    PulseAuthenticationError,
    PulseClientConnectionError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
)
from .pulse_backoff import PulseBackoff
from .pulse_query_manager import PulseQueryManager
from .pulse_connection_status import PulseConnectionStatus
from .pulse_connection_properties import PulseConnectionProperties
from .pulse_authentication_properties import PulseAuthenticationProperties

LOG = logging.getLogger(__name__)

# Pulse allows at most this many characters in a trusted device name
ADT_MAX_DEVICE_NAME_LENGTH = 30


class _PulseMFACommandError(PulseAuthenticationError):
    """An MFA command Pulse answered with an error status."""

    def __init__(self, status: int):
        super().__init__()
        self.status = status


SESSION_COOKIES = {"X-mobile-browser": "false", "ICLocal": "en_US"}


class PulseConnection(PulseQueryManager):
    """ADT Pulse connection related attributes."""

    __slots__ = (
        "_authentication_properties",
        "_login_backoff",
        "_login_in_progress",
        "_mfa_challenge",
        "_pc_attribute_lock",
    )

    @typechecked
    def __init__(
        self,
        pulse_connection_status: PulseConnectionStatus,
        pulse_connection_properties: PulseConnectionProperties,
        pulse_authentication: PulseAuthenticationProperties,
        debug_locks: bool = False,
    ):
        """Initialize ADT Pulse connection."""
        # need to initialize this after the session since we set cookies
        # based on it
        super().__init__(
            pulse_connection_status,
            pulse_connection_properties,
            debug_locks,
        )
        self._pc_attribute_lock = set_debug_lock(
            debug_locks, "pyadtpulse.pc_attribute_lock"
        )
        self._connection_properties = pulse_connection_properties
        self._connection_status = pulse_connection_status
        self._authentication_properties = pulse_authentication
        self._login_backoff = PulseBackoff(
            "Login",
            pulse_connection_status._backoff.initial_backoff_interval,
            detailed_debug_logging=self._connection_properties.detailed_debug_logging,
        )
        self._login_in_progress = False
        self._mfa_challenge: PulseMFAChallenge | None = None
        self._debug_locks = debug_locks

    @typechecked
    def check_login_errors(
        self, response: tuple[int, str | None, URL | None]
    ) -> html.HtmlElement:
        """
        Check response for login errors.

        Will handle setting backoffs and raising exceptions.

        Args:
            response (tuple[int, str | None, URL | None]): The response

        Returns:
            html.HtmlElement: the parsed response tree

        Raises:
            PulseAuthenticationError: if login fails due to incorrect username/password
            PulseServerConnectionError: if login fails due to server error
            PulseAccountLockedError: if login fails due to account locked
            PulseMFARequiredError: if login fails due to MFA required
            PulseNotLoggedInError: if login fails due to not logged in

        """

        def extract_seconds_from_string(s: str) -> int:
            seconds = 0
            match = re.search(r"\d+", s)
            if match:
                seconds = int(match.group())
                if "minutes" in s:
                    seconds *= 60
            return seconds

        def determine_error_type(tree: html.HtmlElement) -> None:
            """
            Determine what type of error we have from the url and the parsed page.

            Will raise the appropriate exception.
            """
            self._login_in_progress = False
            if response_uri.startswith(ADT_LOGIN_URI):
                error = tree.find(
                    path=".//div[@id='warnMsgContents']",
                    namespaces=None,
                )
                if error is not None:
                    error_text = error.text_content()
                    LOG.error("Error logging into pulse: %s", error_text)
                    if "Try again in" in error_text:
                        if (retry_after := extract_seconds_from_string(error_text)) > 0:
                            raise PulseAccountLockedError(
                                self._login_backoff,
                                retry_after + time(),
                            )
                    elif "You have not yet signed in" in error_text:
                        raise PulseNotLoggedInError()
                    elif "Sign In Unsuccessful" in error_text:
                        raise PulseAuthenticationError()
                else:
                    LOG.error("Unknown error logging into pulse: no message given")
                    raise PulseNotLoggedInError()
            elif response_uri == ADT_MFA_FAIL_URI:
                self._mfa_challenge = PulseMFAChallenge.from_page(response[1])
                raise PulseMFARequiredError(self._mfa_challenge)

        tree = make_etree(
            response[0],
            response[1],
            response[2],
            logging.ERROR,
            "Could not log into ADT Pulse site",
        )
        # this probably should have been handled by async_query()
        if tree is None:
            raise PulseServerConnectionError(
                f"Could not log into ADT Pulse site: code {response[0]}: "
                f"URL: {response[2]}, response: {response[1]}",
                self._login_backoff,
            )
        response_url_string = str(response[2])
        # Pulse serves more than one API version at once and can answer a
        # request for one version with a redirect into another, so compare
        # only the part of the URL after the version.
        response_version, response_uri = (
            self._connection_properties.split_versioned_url(response_url_string)
        )
        # adopt it before anything else: MFA calls go to the landed version
        if (
            response_uri in (ADT_SUMMARY_URI, ADT_MFA_FAIL_URI)
            and response_version is not None
            and response_version != self._connection_properties.api_version
        ):
            LOG.debug(
                "Pulse API version changed from %s to %s during login",
                self._connection_properties.api_version,
                response_version,
            )
            self._connection_properties.api_version = response_version
        if response_uri != ADT_SUMMARY_URI:
            determine_error_type(tree=tree)
            # if we get here we can't determine the error
            # raise a generic authentication error
            LOG.error(
                "Login received unexpected response from login query: %s",
                response_url_string,
            )
            raise PulseAuthenticationError()
        return tree

    @typechecked
    async def async_do_login_query(
        self, timeout: int = ADT_DEFAULT_LOGIN_TIMEOUT
    ) -> html.HtmlElement | None:
        """
        Perform a login query to the Pulse site.

        Will backoff on login failures.

        Will set login in progress flag.

        Args:
            timeout (int, optional): The timeout value for the query in seconds.
            Defaults to ADT_DEFAULT_LOGIN_TIMEOUT.

        Returns:
            tree (html.HtmlElement, optional): the parsed response tree for
            summary.jsp, or None if failure
        Raises:
            ValueError: if login parameters are not correct
            PulseAuthenticationError: if login fails due to incorrect username/password
            PulseServerConnectionError: if login fails due to server error
            PulseServiceTemporarilyUnavailableError: if login fails due to too many
                requests or server is temporarily unavailable
            PulseAccountLockedError: if login fails due to account locked
            PulseMFARequiredError: if login fails due to MFA required
            PulseNotLoggedInError: if login fails due to not logged in
                (which is probably an internal error)

        """
        if self.login_in_progress:
            return None
        await self.quick_logout()
        # just raise exceptions if we're not going to be able to log in
        lockout_time = self._login_backoff.expiration_time
        if lockout_time > time():
            raise PulseAccountLockedError(self._login_backoff, lockout_time)
        cs_backoff = self._connection_status.get_backoff()
        lockout_time = cs_backoff.expiration_time
        if lockout_time > time():
            raise PulseServiceTemporarilyUnavailableError(cs_backoff, lockout_time)
        self.login_in_progress = True
        data = {
            "usernameForm": self._authentication_properties.username,
            "passwordForm": self._authentication_properties.password,
            "fingerprint": self._authentication_properties.fingerprint,
        }
        if self._authentication_properties.site_id:
            data["networkid"] = self._authentication_properties.site_id
        await self._login_backoff.wait_for_backoff()
        try:
            response = await self.async_query(
                ADT_LOGIN_URI,
                "POST",
                extra_params=data,
                timeout=timeout,
                requires_authentication=False,
            )
        except (
            PulseClientConnectionError,
            PulseServerConnectionError,
            PulseServiceTemporarilyUnavailableError,
        ) as e:
            LOG.error("Could not log into Pulse site: %s", e)
            self.login_in_progress = False
            raise
        tree = self.check_login_errors(response)
        self._login_succeeded()
        return tree

    def _login_succeeded(self) -> None:
        self._mfa_challenge = None
        self._connection_status.authenticated_flag.set()
        self._authentication_properties.last_login_time = int(time())
        self._login_backoff.reset_backoff()
        self.login_in_progress = False

    async def _async_mfa_query(
        self,
        href: str,
        method: str = "GET",
        data: dict[str, str] | None = None,
        x_token: str | None = None,
    ) -> dict:
        """
        Call an MFA REST command through the Pulse proxy and decode its JSON.

        Raises:
            PulseNotLoggedInError: if no MFA challenge is pending
            _PulseMFACommandError: if Pulse refuses the command (HTTP 4xx)
            PulseServerConnectionError: if Pulse fails (HTTP 5xx, a network
                error, or an answer that is not JSON)
            PulseServiceTemporarilyUnavailableError: if Pulse answers HTTP 429
                or 503, or asked earlier to wait and that time has not passed

        """
        challenge = self._mfa_challenge
        if challenge is None:
            raise PulseNotLoggedInError()
        secrets_to_mask = (
            challenge.pre_auth_token,
            x_token,
            (data or {}).get("otp"),
        )
        # Not async_query: Pulse answers a rejected code with HTTP 400 and a JSON
        # detail, which async_query would report as a server error (bumping the
        # connection backoff), and an OTP must not be retried. So honor a
        # Retry-After here, without sending anything, instead.
        retry_after = self._connection_status.retry_after
        if retry_after > time():
            raise PulseServiceTemporarilyUnavailableError(
                self._connection_status.get_backoff(), retry_after
            )
        url = self._connection_properties.make_url(challenge.proxy_url(href))
        try:
            async with self._connection_properties.session.request(
                method,
                url,
                headers=challenge.headers(x_token),
                data=data if method == "POST" else None,
                timeout=ClientTimeout(total=float(ADT_DEFAULT_LOGIN_TIMEOUT)),
            ) as response:
                status = response.status
                text = await response.text()
                retry_header = response.headers.get("Retry-After")
        # asyncio.TimeoutError is a separate class before Python 3.11
        except (ClientError, asyncio.TimeoutError, UnicodeDecodeError) as ex:
            raise PulseServerConnectionError(
                f"MFA command {href} failed: {ex}",
                self._connection_status.get_backoff(),
            ) from ex
        try:
            result = json.loads(text or "")
        except ValueError:
            result = None
        detail = result.get("detail") if isinstance(result, dict) else None
        if status == HTTPStatus.TOO_MANY_REQUESTS or status >= 500:
            # An outage or rate limit, even with a JSON body: never report it as
            # a wrong code. Raises PulseServiceTemporarilyUnavailableError, with
            # the Retry-After time, for 429 and 503, else
            # PulseServerConnectionError. Not retried: an OTP may work only once.
            LOG.error(
                "Pulse MFA command %s returned HTTP %s: %s",
                href,
                status,
                mask_mfa_secrets(detail, *secrets_to_mask),
            )
            self._handle_http_errors(
                (
                    status,
                    mask_mfa_secrets(detail, *secrets_to_mask),
                    URL(url),
                    retry_header,
                )
            )
        if result is None:
            # not an answer to the command, such as a gateway error page
            raise PulseServerConnectionError(
                f"MFA command {href} returned HTTP {status}, not JSON",
                self._connection_status.get_backoff(),
            )
        if status != 200 or not isinstance(result, dict):
            # HTTP 4xx: Pulse refused the command, such as 400 for a wrong code
            # or 409 for a device name already in use
            LOG.error(
                "Pulse MFA command %s returned HTTP %s: %s",
                href,
                status,
                mask_mfa_secrets(
                    detail if detail is not None else result, *secrets_to_mask
                ),
            )
            raise _PulseMFACommandError(status)
        return result

    def _pre_auth_token_for_logs(self) -> str | None:
        """Return the pending pre-auth token, to mask it in logs."""
        challenge = self._mfa_challenge
        return challenge.pre_auth_token if challenge is not None else None

    async def _async_mfa_command(self, name: str) -> dict:
        """Return the MFA command the server currently offers under name."""
        state = await self._async_mfa_query(ADT_MFA_STATE_HREF)
        command = state.get("commands", {}).get(name)
        if not command or not command.get("action"):
            LOG.error("Pulse did not offer the MFA command %s", name)
            raise PulseAuthenticationError()
        return command

    async def async_request_mfa_code(self, method_id: str | None = None) -> str:
        """
        Ask Pulse to send a verification code for the pending MFA challenge.

        Args:
            method_id (str, optional): the verification method, such as "EMAIL".
                Defaults to the first method registered on the account.

        Returns:
            str: the id of the method the code was sent with

        Raises:
            PulseNotLoggedInError: if no MFA challenge is pending
            PulseAuthenticationError: if Pulse refuses the request
            PulseServerConnectionError: if Pulse fails, such as an HTTP 5xx
            PulseServiceTemporarilyUnavailableError: if Pulse answers HTTP 429
                or 503, or asked earlier to wait and that time has not passed

        """
        command = await self._async_mfa_command("requestOtpForRegisteredProperty")
        options = command.get("params", {}).get("id", {}).get("options", [])
        ids = [o.get("value") for o in options if o.get("value")]
        if method_id is None:
            if not ids:
                LOG.error("No MFA verification method is registered")
                raise PulseAuthenticationError()
            method_id = ids[0]
        sent = await self._async_mfa_query(command["action"], "POST", {"id": method_id})
        # The portal answers a sent code with {"code": 0, "detail": "OK"}, as
        # observed on the live portal; anything else means no code was sent.
        if sent.get("detail") != "OK":
            LOG.error(
                "Pulse did not send an MFA verification code: %s",
                mask_mfa_secrets(sent, self._pre_auth_token_for_logs()),
            )
            raise PulseAuthenticationError()
        return method_id

    async def async_submit_mfa_code(
        self, code: str, device_name: str = "pyadtpulse"
    ) -> html.HtmlElement:
        """
        Finish the pending MFA login with a verification code.

        The device is also added to the account's trusted devices, so later
        logins with the same fingerprint skip MFA. If Pulse refuses that, the
        login still succeeds and a warning is logged.

        Args:
            code (str): the verification code Pulse sent
            device_name (str): the name to trust this device under

        Returns:
            html.HtmlElement: the parsed summary page

        Raises:
            PulseNotLoggedInError: if no MFA challenge is pending, or the login
                fails after the code was accepted (start over)
            PulseAuthenticationError: if Pulse rejects the code
            PulseServerConnectionError: if Pulse fails, such as an HTTP 5xx
            PulseServiceTemporarilyUnavailableError: if Pulse answers HTTP 429
                or 503, or asked earlier to wait and that time has not passed

        """
        command = await self._async_mfa_command("validateOtp")
        validated = await self._async_mfa_query(
            command["action"], "POST", {"otp": code.strip()}
        )
        x_token = validated.get("detail")
        # The portal answers an accepted code with the X-token in "detail": a
        # signed string ending in "sig=...", as observed on the live portal.
        # Anything else means the code was not accepted.
        if not isinstance(x_token, str) or "sig=" not in x_token:
            LOG.error(
                "Pulse rejected the MFA verification code: %s",
                mask_mfa_secrets(
                    validated, self._pre_auth_token_for_logs(), code.strip()
                ),
            )
            raise PulseAuthenticationError()
        # Pulse offers addTrustedDevice only once the code is validated, and the
        # web client sends the name URL-encoded inside the form body.
        trust_href = command["action"].rsplit("/", 1)[0] + "/addTrustedDevice"
        # Best effort: the code is validated, so the login stands either way;
        # only the next login needs MFA again. Names must be unique in the
        # account (HTTP 409 otherwise), so retry once with a suffix.
        trusted: dict = {}
        unique = (
            f"{device_name[: ADT_MAX_DEVICE_NAME_LENGTH - 5]} {secrets.token_hex(2)}"
        )
        for name in (device_name[:ADT_MAX_DEVICE_NAME_LENGTH], unique):
            try:
                trusted = await self._async_mfa_query(
                    trust_href, "POST", {"name": quote(name)}, x_token=x_token
                )
            except _PulseMFACommandError as ex:
                if ex.status == HTTPStatus.CONFLICT:
                    continue
            # a server error, rate limit or timeout; any Retry-After it carried
            # still applies to the sign-in below
            except PulseConnectionError:
                pass
            break
        # The portal answers a trusted device with {"code": 0, "detail": "OK"},
        # as observed on the live portal.
        if trusted.get("detail") != "OK":
            LOG.warning(
                "Pulse did not trust this device: %s",
                mask_mfa_secrets(trusted, self._pre_auth_token_for_logs(), x_token),
            )
        # the code is spent: a retry after a failure below must start over
        self._mfa_challenge = None
        response = await self.async_query(
            ADT_POST_SIGNIN_URI,
            timeout=ADT_DEFAULT_LOGIN_TIMEOUT,
            requires_authentication=False,
        )
        try:
            tree = self.check_login_errors(response)
        except PulseAuthenticationError as ex:
            # the code was accepted, so this is not a wrong code
            raise PulseNotLoggedInError() from ex
        self._login_succeeded()
        return tree

    @typechecked
    async def async_do_logout_query(self, site_id: str | None = None) -> None:
        """Perform a logout query to the ADT Pulse site."""
        params = {}
        si = ""
        self._connection_status.authenticated_flag.clear()
        if site_id is not None and site_id != "":
            self._authentication_properties.site_id = site_id
            si = site_id
        params.update({"networkid": si})

        params.update({"partner": "adt"})
        try:
            await self.async_query(
                ADT_LOGOUT_URI,
                extra_params=params,
                timeout=10,
                requires_authentication=False,
            )
        # FIXME: do we care if this raises exceptions?
        except (
            PulseClientConnectionError,
            PulseServiceTemporarilyUnavailableError,
            PulseServerConnectionError,
        ) as e:
            LOG.debug("Could not logout from Pulse site: %s", e)

    @property
    def is_connected(self) -> bool:
        """Check if ADT Pulse is connected."""
        return (
            self._connection_status.authenticated_flag.is_set()
            and not self._login_in_progress
        )

    @property
    def login_backoff(self) -> PulseBackoff:
        """Return backoff object."""
        with self._pc_attribute_lock:
            return self._login_backoff

    def check_sync(self, message: str) -> AbstractEventLoop:
        """Check if run from sync context (Convenience method)."""
        return self._connection_properties.check_sync(message)

    @property
    def debug_locks(self):
        """Return debug locks."""
        return self._debug_locks

    @property
    def login_in_progress(self) -> bool:
        """Return login in progress."""
        with self._pc_attribute_lock:
            return self._login_in_progress

    @login_in_progress.setter
    @typechecked
    def login_in_progress(self, value: bool) -> None:
        """Set login in progress."""
        with self._pc_attribute_lock:
            self._login_in_progress = value

    async def quick_logout(self) -> None:
        """
        Quickly logout.

        This just resets the authenticated flag and clears the ClientSession.
        """
        LOG.debug("Resetting session")
        self._mfa_challenge = None
        self._connection_status.authenticated_flag.clear()
        await self._connection_properties.clear_session()

    @property
    def detailed_debug_logging(self) -> bool:
        """Return detailed debug logging."""
        return (
            self._login_backoff.detailed_debug_logging
            and self._connection_properties.detailed_debug_logging
            and self._connection_status.detailed_debug_logging
        )

    @detailed_debug_logging.setter
    @typechecked
    def detailed_debug_logging(self, value: bool):
        with self._pc_attribute_lock:
            self._login_backoff.detailed_debug_logging = value
            self._connection_properties.detailed_debug_logging = value
            self._connection_status.detailed_debug_logging = value

    def get_login_backoff(self) -> PulseBackoff:
        """Return login backoff."""
        return self._login_backoff
