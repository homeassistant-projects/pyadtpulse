#!/usr/bin/env python
"""
Sample client for using pyadtpulse.

Logs in with PyADTPulseAsync, asking for a verification code on the terminal
if ADT requires one, then prints the site and every update until Ctrl-C.

Parameters come from the command line, a JSON file (see example-client.json),
or the ADTPULSE_USER, ADTPULSE_PASSWORD and ADTPULSE_FINGERPRINT environment
variables, in that order.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from time import time
from pprint import pprint

from pyadtpulse.site import ADTPulseSite
from pyadtpulse.const import (
    API_HOST_CA,
    DEFAULT_API_HOST,
    ADT_DEFAULT_POLL_INTERVAL,
    ADT_DEFAULT_RELOGIN_INTERVAL,
    ADT_DEFAULT_KEEPALIVE_INTERVAL,
)
from pyadtpulse.exceptions import (
    PulseLoginException,
    PulseMFARequiredError,
    PulseNotLoggedInError,
    PulseAccountLockedError,
    PulseAuthenticationError,
    PulseGatewayOfflineError,
    PulseClientConnectionError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
)
from pyadtpulse.pyadtpulse_async import PyADTPulseAsync

USER = "adtpulse_user"
PASSWD = "adtpulse_password"
FINGERPRINT = "adtpulse_fingerprint"
PULSE_DEBUG = "debug"
TEST_ALARM = "test_alarm"
SLEEP_INTERVAL = "sleep_interval"
USE_ASYNC = "use_async"
DEBUG_LOCKS = "debug_locks"
KEEPALIVE_INTERVAL = "keepalive_interval"
RELOGIN_INTERVAL = "relogin_interval"
SERVICE_HOST = "service_host"
POLL_INTERVAL = "poll_interval"
DETAILED_DEBUG_LOGGING = "detailed_debug_logging"
DEVICE_NAME = "device_name"
MFA_METHOD = "mfa_method"

BOOLEAN_PARAMS = {
    USE_ASYNC,
    DEBUG_LOCKS,
    PULSE_DEBUG,
    TEST_ALARM,
    DETAILED_DEBUG_LOGGING,
}
INT_PARAMS = {SLEEP_INTERVAL, KEEPALIVE_INTERVAL, RELOGIN_INTERVAL}
FLOAT_PARAMS = {POLL_INTERVAL}
STRING_PARAMS = {USER, PASSWD, FINGERPRINT, SERVICE_HOST, DEVICE_NAME, MFA_METHOD}

# Default values
DEFAULT_DEBUG = False
DEFAULT_DETAILED_DEBUG_LOGGING = False
DEFAULT_TEST_ALARM = False
DEFAULT_DEBUG_LOCKS = False
DEFAULT_DEVICE_NAME = "pyadtpulse example client"

# Constants for environment variable names
ENV_USER = "ADTPULSE_USER"
ENV_PASSWORD = "ADTPULSE_PASSWORD"
ENV_FINGERPRINT = "ADTPULSE_FINGERPRINT"


def setup_logger(level: int):
    """Set up logger."""
    logger = logging.getLogger()
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter("%(asctime)s %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def str_to_bool(value: str) -> bool:
    """
    Parse a boolean command line value such as True, false, yes, 0.

    argparse's type=bool treats every non-empty string, "False" included, as True.
    """
    lowered = value.strip().lower()
    if lowered in ("1", "true", "yes", "y", "on"):
        return True
    if lowered in ("0", "false", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError(f"expected True or False, got {value!r}")


def handle_args() -> argparse.Namespace:
    """
    Handle program arguments using argparse.

    Returns:
        argparse.Namespace: Parsed command-line arguments.

    """
    parser = argparse.ArgumentParser(description="ADT Pulse example client")
    parser.add_argument("json_file", nargs="?", help="JSON file containing parameters")
    parser.add_argument(
        f"--{USER}",
        help=f"Pulse username (can be set in JSON file or ${ENV_USER})",
    )
    parser.add_argument(
        f"--{PASSWD}",
        help=f"Pulse password (can be set in JSON file or ${ENV_PASSWORD})",
    )
    parser.add_argument(
        f"--{FINGERPRINT}",
        help=f"Pulse fingerprint (can be set in JSON file or ${ENV_FINGERPRINT})",
    )
    parser.add_argument(
        f"--{SERVICE_HOST}",
        help=f"Pulse service host, must be {DEFAULT_API_HOST} or {API_HOST_CA}, "
        f"default is {DEFAULT_API_HOST}",
    )
    parser.add_argument(
        f"--{DEVICE_NAME}",
        help="Name to trust this fingerprint under if ADT asks for a "
        f"verification code (default: {DEFAULT_DEVICE_NAME!r})",
    )
    parser.add_argument(
        f"--{MFA_METHOD}",
        help="Verification code method id, such as EMAIL "
        "(default: the first method registered on the account)",
    )
    parser.add_argument(
        f"--{PULSE_DEBUG}",
        type=str_to_bool,
        default=None,
        help="Set True to enable debugging",
    )
    parser.add_argument(
        f"--{DETAILED_DEBUG_LOGGING}",
        type=str_to_bool,
        default=None,
        help="Set True to enable detailed debug logging",
    )
    parser.add_argument(
        f"--{TEST_ALARM}",
        type=str_to_bool,
        default=None,
        help="Set True to test alarm arming/disarming. This really arms and "
        "disarms your alarm",
    )
    parser.add_argument(
        f"--{SLEEP_INTERVAL}",
        type=int,
        default=None,
        help="Deprecated and ignored: only the removed sync example used it",
    )
    parser.add_argument(
        f"--{USE_ASYNC}",
        type=str_to_bool,
        default=None,
        help="Deprecated and ignored: the example always uses PyADTPulseAsync",
    )
    parser.add_argument(
        f"--{DEBUG_LOCKS}",
        type=str_to_bool,
        default=None,
        help=f"Set to true to debug thread locks, default: {DEFAULT_DEBUG_LOCKS}",
    )
    parser.add_argument(
        f"--{KEEPALIVE_INTERVAL}",
        type=int,
        default=None,
        help="Number of minutes to wait between keepalive calls (default: "
        f"{ADT_DEFAULT_KEEPALIVE_INTERVAL} minutes)",
    )
    parser.add_argument(
        f"--{RELOGIN_INTERVAL}",
        type=int,
        default=None,
        help="Number of minutes to wait between relogin calls "
        f"(default: {ADT_DEFAULT_RELOGIN_INTERVAL} minutes)",
    )
    parser.add_argument(
        f"--{POLL_INTERVAL}",
        type=float,
        default=None,
        help="Number of seconds to wait between polling calls "
        f"(default: {ADT_DEFAULT_POLL_INTERVAL} seconds)",
    )

    args = parser.parse_args()

    # Command line values win over the JSON file, which wins over the environment.
    # load_parameters_from_json() drops values of the wrong type.
    if args.json_file is not None:
        json_params = load_parameters_from_json(args.json_file)
        if json_params is not None:
            for key, value in json_params.items():
                if not hasattr(args, key):
                    print(f"Unknown parameter {key} in JSON file, ignoring...")
                    continue
                if getattr(args, key) is None and value is not None:
                    setattr(args, key, value)
    for key, env in (
        (USER, ENV_USER),
        (PASSWD, ENV_PASSWORD),
        (FINGERPRINT, ENV_FINGERPRINT),
    ):
        if getattr(args, key) is None:
            setattr(args, key, os.environ.get(env))

    if args.use_async is False:
        print(
            f"{USE_ASYNC}=False is no longer supported: pyadtpulse 2.0 removed the "
            "sync PyADTPulse client. Using PyADTPulseAsync."
        )

    def default(value, fallback):
        return value if value is not None else fallback

    args.debug_locks = default(args.debug_locks, DEFAULT_DEBUG_LOCKS)
    args.debug = default(args.debug, DEFAULT_DEBUG)
    args.detailed_debug_logging = default(
        args.detailed_debug_logging, DEFAULT_DETAILED_DEBUG_LOGGING
    )
    args.test_alarm = default(args.test_alarm, DEFAULT_TEST_ALARM)
    args.keepalive_interval = default(
        args.keepalive_interval, ADT_DEFAULT_KEEPALIVE_INTERVAL
    )
    args.relogin_interval = default(args.relogin_interval, ADT_DEFAULT_RELOGIN_INTERVAL)
    args.service_host = default(args.service_host, DEFAULT_API_HOST)
    args.poll_interval = default(args.poll_interval, ADT_DEFAULT_POLL_INTERVAL)
    args.device_name = default(args.device_name, DEFAULT_DEVICE_NAME)

    return args


def load_parameters_from_json(json_file: str) -> dict | None:
    """
    Load parameters from a JSON file.

    Args:
        json_file (str): Path to the JSON file.

    Returns:
        Optional[Dict]: Loaded parameters as a dictionary,
                        or None if there was an error.

    """
    try:
        with open(json_file, encoding="utf-8") as file:
            parameters = json.load(file)
    except FileNotFoundError:
        print(f"JSON file not found: {json_file}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None
    invalid_keys = []
    for key, value in parameters.items():
        if key in BOOLEAN_PARAMS and not isinstance(value, bool):
            kind = "boolean"
        elif key in INT_PARAMS and (
            not isinstance(value, int) or isinstance(value, bool)
        ):
            kind = "integer"
        elif key in FLOAT_PARAMS and (
            not isinstance(value, (int, float)) or isinstance(value, bool)
        ):
            kind = "float"
        elif key in STRING_PARAMS and not isinstance(value, str):
            kind = "string"
        else:
            continue
        print(f"Invalid {kind} value for {key}: {value} in JSON file, ignoring...")
        invalid_keys.append(key)
    for key in invalid_keys:
        del parameters[key]
    return parameters


def print_site(site: ADTPulseSite) -> None:
    """
    Print site information.

    Args:
        site (ADTPulseSite): The site to display

    """
    print(f"Site: {site.name} (id={site.id})")
    print("Alarm panel: ")
    pprint(site.alarm_control_panel, compact=True)
    print("Gateway: ")
    pprint(site.gateway, compact=True)


async def async_test_alarm(adt: PyADTPulseAsync) -> None:
    """
    Test alarm functions.

    Args:
        adt (PyADTPulseAsync): ADT Pulse connection object

    """
    print("Arming alarm stay")
    if await adt.site.async_arm_home():
        print("Arming stay call succeeded")
        if adt.site.alarm_control_panel.is_arming:
            print("Arming stay pending check succeeded")
        else:
            print(
                "FAIL: Arming home pending check failed "
                f"{adt.site.alarm_control_panel} "
            )
        await adt.wait_for_update()
        if adt.site.alarm_control_panel.is_home:
            print("Arm stay no longer pending")
        else:
            while not adt.site.alarm_control_panel.is_home:
                pprint(f"FAIL: Arm stay value incorrect {adt.site.alarm_control_panel}")
                await adt.wait_for_update()
        print("Testing invalid alarm state change from armed home to armed away")
        if await adt.site.async_arm_away():
            print(
                f"FAIL: armed away while already armed {adt.site.alarm_control_panel}"
            )
        else:
            print("Test succeeded")
            print("Testing changing alarm status to same value")
            if await adt.site.async_arm_home():
                print(
                    f"FAIL: allowed arming to same state {adt.site.alarm_control_panel}"
                )
            else:
                print("Test succeeded")

    else:
        print("Alarm arming home failed, attempting force arm")
        if await adt.site.async_arm_home(True):
            print("Force arm succeeded")
        else:
            print(f"FAIL: Force arm failed {adt.site.alarm_control_panel}")
    print("Disarming alarm")
    if await adt.site.async_disarm():
        print("Disarming succeeded")
        if adt.site.alarm_control_panel.is_disarming:
            print("Disarm pending success")
        else:
            pprint(f"FAIL: Disarm pending fail {adt.site.alarm_control_panel}")
        await adt.wait_for_update()
        if adt.site.alarm_control_panel.is_disarmed:
            print("Success update to disarm")
        else:
            while not adt.site.alarm_control_panel.is_disarmed:
                pprint(
                    "FAIL: did not set to disarm after update "
                    f"{adt.site.alarm_control_panel}"
                )
                await adt.wait_for_update()
        print("Test finally succeeded")
        print("Testing disarming twice")
        if await adt.site.async_disarm():
            print("Double disarm call succeeded")
        else:
            pprint(f"FAIL: Double disarm call failed {adt.site.alarm_control_panel}")
        if adt.site.alarm_control_panel.is_disarming:
            print("Double disarm state is disarming")
        else:
            pprint(
                "FAIL: Double disarm state is not disarming "
                f"{adt.site.alarm_control_panel}"
            )
        await adt.wait_for_update()
        if adt.site.alarm_control_panel.is_disarmed:
            print("Double disarm success")
        else:
            while not adt.site.alarm_control_panel.is_disarmed:
                pprint(
                    "FAIL: Double disarm state is not disarmed "
                    f"{adt.site.alarm_control_panel}"
                )
                await adt.wait_for_update()
        print("Test finally succeeded")
    else:
        print("Disarming failed")
    print("Arming alarm away")
    if await adt.site.async_arm_away():
        print("Arm away call succeeded")
        if adt.site.alarm_control_panel.is_arming:
            print("Arm away arm pending")
        else:
            pprint(f"FAIL: arm away call not pending {adt.site.alarm_control_panel}")
        await adt.wait_for_update()
        if adt.site.alarm_control_panel.is_away:
            print("Arm away call after update succeed")
        else:
            while not adt.site.alarm_control_panel.is_away:
                pprint(
                    "FAIL: arm away call after update failed "
                    f"{adt.site.alarm_control_panel}"
                )
                await adt.wait_for_update()
        print("Test finally succeeded")
    else:
        print("Arm away failed")
    await adt.site.async_disarm()
    print("Disarmed")


async def async_mfa_login(
    adt: PyADTPulseAsync, device_name: str, mfa_method: str | None
) -> bool:
    """
    Finish a login that needs a verification code, reading it from the terminal.

    Call this after async_login() raised PulseMFARequiredError.

    Args:
        adt (PyADTPulseAsync): the client whose login needs a code
        device_name (str): name to trust the fingerprint under
        mfa_method (str | None): verification method id, None for the default

    Returns:
        bool: True if logged in, False to start the login over

    """
    try:
        method = await adt.async_request_mfa_code(mfa_method)
    except PulseNotLoggedInError:
        print("No verification challenge is pending, starting over")
        return False
    except PulseAuthenticationError:
        print("ADT refused to send a verification code, starting over")
        return False
    print(f"ADT sent a verification code ({method})")
    while True:
        code = input("Verification code (empty to start over): ").strip()
        if not code:
            return False
        try:
            await adt.async_complete_mfa_login(code, device_name)
        except PulseAuthenticationError:
            print("ADT rejected the code, try again")
            continue
        except PulseNotLoggedInError:
            print("The login failed after the code, starting over")
            return False
        print(f"Logged in. This fingerprint is now trusted as {device_name!r}")
        return True


async def async_login(
    adt: PyADTPulseAsync, device_name: str, mfa_method: str | None
) -> bool:
    """
    Log in, retrying connection errors and asking for a verification code.

    Returns:
        bool: True if logged in

    """
    while True:
        try:
            await adt.async_login()
            return True
        except PulseMFARequiredError:
            print("ADT requires a verification code for this fingerprint")
            if await async_mfa_login(adt, device_name, mfa_method):
                return True
            continue
        except PulseAccountLockedError as e:
            print(f"ADT Pulse account is locked: {e}")
            return False
        except PulseLoginException as e:
            print(f"ADT Pulse login failed with authentication error: {e}")
            return False
        except (PulseClientConnectionError, PulseServerConnectionError) as e:
            backoff_interval = e.backoff.get_current_backoff_interval()
            print(
                f"ADT Pulse login failed with connection error: {e}, "
                f"retrying in {backoff_interval} seconds"
            )
            await asyncio.sleep(backoff_interval)
        except PulseServiceTemporarilyUnavailableError as e:
            backoff_interval = max(e.backoff.expiration_time - time(), 0)
            print(
                f"ADT Pulse login failed with service unavailable error: {e}, "
                f"retrying in {backoff_interval} seconds"
            )
            await asyncio.sleep(backoff_interval)


async def async_example(args: argparse.Namespace) -> None:
    """
    Run example of pyadtpulse async usage.

    Args:
        args (argparse.Namespace): parameters from handle_args()

    """
    adt = PyADTPulseAsync(
        args.adtpulse_user,
        args.adtpulse_password,
        args.adtpulse_fingerprint,
        service_host=args.service_host,
        debug_locks=args.debug_locks,
        keepalive_interval=args.keepalive_interval,
        relogin_interval=args.relogin_interval,
        detailed_debug_logging=args.detailed_debug_logging,
    )

    if not await async_login(adt, args.device_name, args.mfa_method):
        return

    try:
        await async_watch(adt, args.poll_interval, args.test_alarm)
    finally:
        print("Logging out")
        await adt.async_logout()


async def async_watch(
    adt: PyADTPulseAsync, poll_interval: float, run_alarm_test: bool
) -> None:
    """Print the site, then every update, until an error or Ctrl-C."""
    if not adt.is_connected:
        print("Error: could not log into ADT Pulse site")
        return

    print_site(adt.site)
    if not adt.site.zones:
        print("Error: no zones exist")
        return
    adt.site.gateway.poll_interval = poll_interval
    pprint(adt.site.zones, compact=True)
    if run_alarm_test:
        await async_test_alarm(adt)

    have_exception = False
    while True:
        if not have_exception:
            print(f"Gateway online: {adt.site.gateway.is_online}")
            print_site(adt.site)
            print("----")
            if not adt.site.zones:
                print("No zones exist, exiting...")
                return
            print("\nZones:")
            pprint(adt.site.zones, compact=True)
        try:
            (alarm_updated, updated_zones) = await adt.wait_for_update()
            have_exception = False
        except PulseGatewayOfflineError as ex:
            print(
                "ADT Pulse gateway is offline, re-polling in "
                f"{ex.backoff.get_current_backoff_interval()}"
            )
            have_exception = True
            continue
        except (PulseClientConnectionError, PulseServerConnectionError) as ex:
            print(
                f"ADT Pulse connection error: {ex.args[0]}, re-polling in "
                f"{ex.backoff.get_current_backoff_interval()}"
            )
            have_exception = True
            continue
        except PulseLoginException as ex:
            # The background relogin failed (bad password, new verification
            # code needed, account locked...). Run the example again.
            print(f"ADT Pulse login error: {ex}, exiting...")
            return
        print(
            f"Updates exist: alarm: {alarm_updated}, zones: {updated_zones}, "
            "refreshing",
        )


def main():
    """Run main program."""
    args = handle_args()

    if not all([args.adtpulse_user, args.adtpulse_password, args.adtpulse_fingerprint]):
        print(f"ERROR! {USER}, {PASSWD}, and {FINGERPRINT} must all be set")
        raise SystemExit(1)

    setup_logger(logging.DEBUG if args.debug else logging.ERROR)

    try:
        asyncio.run(async_example(args))
    except KeyboardInterrupt:
        print("exiting...")


if __name__ == "__main__":
    main()
