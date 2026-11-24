# pyadtpulse - Python interface for ADT Pulse

Python client interface to the ADT Pulse security system.

[![PyPi](https://img.shields.io/pypi/v/pyadtpulse.svg)](https://pypi.python.org/pypi/pyadtpulse)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

## UNSUPPORTED

**This is an unsupported interface provided only as a basis for others to explore integrating
their ADT system with their own tools.** PLEASE FEEL FREE TO CONTRIBUTE CHANGES! Pull requests are accepted.

pyadtpulse reads the zones (motion sensors, door sensors, etc.) and alarm state of an
ADT Pulse site, and arms and disarms it. Its main user is the
[Home Assistant ADT Pulse integration](https://github.com/homeassistant-projects/hass-adtpulse).

NOTE: Since this interacts with the unofficial ADT Pulse web portal, the
behavior is subject to change by ADT without notice.

## Making Contributions

Want to contribute? See the [Development](./DEVELOPMENT.md) documentation for setup instructions.

## WARNING

Do not reauthenticate to the ADT service frequently as ADT's service is not designed for high
volume requests. E.g. every 5 minutes, not seconds. Keep your authenticated session to avoid
logging in repeatedly.

## Installation

```
pip install pyadtpulse
```

pyadtpulse needs Python 3.10 or newer.

## Usage

ADT Pulse logs out other sessions that use the same account and fingerprint, so a best
practice is to **create a separate username/password for each client** accessing ADT Pulse.

pyadtpulse uses one site (premises/location) per login. If your account has several sites,
create a separate username/password for each site, with access to only that site. This
ensures that clients are always interacting with that one site (and not accidentally with
another site location).

Changes to the name or number of sites are not picked up by an existing client; create a
new one.

## Example

`PyADTPulseAsync` is the client to use. It logs in, keeps the session alive in the
background and tells you when something changes:

```python
import asyncio

from pyadtpulse import PyADTPulseAsync


async def main() -> None:
    adt = PyADTPulseAsync("user@example.com", "password", "my-fingerprint")
    await adt.async_login()
    try:
        site = adt.site
        print(site.name, site.alarm_control_panel.status)
        for zone in site.zones or []:
            print(zone["zone"], zone["name"], zone["state"], zone["status"])

        while True:
            alarm_changed, zone_ids = await adt.wait_for_update()
            if alarm_changed:
                print("Alarm is now", site.alarm_control_panel.status)
            for zone_id in zone_ids:
                zone = site.zones_as_dict[zone_id]
                print(zone.name, "is now", zone.state)
    finally:
        await adt.async_logout()


asyncio.run(main())
```

- `async_login()` raises `PulseMFARequiredError` when ADT wants a verification code
  first; see [Verification code (MFA) login](#verification-code-mfa-login). Other failures
  raise `PulseAuthenticationError` (wrong username or password), `PulseAccountLockedError`,
  or a connection error, all from `pyadtpulse.exceptions`.
- `adt.site` is the site the login belongs to. `site.zones` is a list of dicts (`zone`,
  `name`, `id_`, `tags`, `status`, `state`, `last_activity_timestamp`); `site.zones_as_dict`
  maps zone ids to the same data as objects.
- `site.alarm_control_panel.status` is one of `"off"`, `"away"`, `"stay"`, `"night"`,
  `"arming"`, `"disarming"` or `"unknown"`. The panel also has `is_disarmed`, `is_away`,
  `is_home`, `is_armed_night`, `is_force_armed`, `is_arming` and `is_disarming`.
- `wait_for_update()` waits until ADT reports a change and returns whether the alarm state
  changed, plus the ids of the zones that did. It raises the error the background tasks
  hit, for example `PulseGatewayOfflineError` or `PulseNotLoggedInError`; call
  `async_login()` again after a `PulseNotLoggedInError`.
- `adt.is_connected` says whether the client currently has a working session.

To arm or disarm the site:

```python
await site.async_disarm()
await site.async_arm_home()  # "stay"
await site.async_arm_away()
await site.async_arm_night()
await site.async_arm_away(force_arm=True)  # arm even with open zones
```

Each returns `True` if ADT accepted the command.

## Verification code (MFA) login

ADT trusts a device by its fingerprint. The first login with a fingerprint ADT doesn't
know makes `async_login()` raise `PulseMFARequiredError`. Finish that login with a
verification code:

```python
from pyadtpulse import PyADTPulseAsync
from pyadtpulse.exceptions import (
    PulseMFARequiredError,
    PulseNotLoggedInError,
    PulseAuthenticationError,
)


async def login(adt: PyADTPulseAsync) -> None:
    try:
        await adt.async_login()
    except PulseMFARequiredError:
        method = await adt.async_request_mfa_code()  # ADT sends the code, e.g. by email
        code = input(f"Code sent by {method}: ")
        try:
            await adt.async_complete_mfa_login(code, device_name="my-script")
        except PulseAuthenticationError:
            ...  # wrong code: ask again, or request a new code
        except PulseNotLoggedInError:
            ...  # the login failed after the code: start over with async_login()
```

- `async_request_mfa_code(method_id=None)` asks ADT to send a code with the first
  verification method on the account, or with `method_id` (such as `"EMAIL"`). It returns
  the method used. It raises `PulseAuthenticationError` if ADT refuses, and
  `PulseNotLoggedInError` if no verification is pending (log in again first).
- `async_complete_mfa_login(code, device_name="pyadtpulse")` checks the code and finishes
  the login, like `async_login()`.
  - **`PulseAuthenticationError`**: ADT rejected the code. The verification is still
    pending, so you can call `async_complete_mfa_login()` again with the right code, or
    `async_request_mfa_code()` for a new one.
  - **`PulseNotLoggedInError`**: no verification was pending, or ADT accepted the code but
    the login still failed. The code is spent; start over with `async_login()`.
- After a correct code, pyadtpulse adds the fingerprint to the account's trusted devices
  under `device_name` (with a short suffix if the name is taken). Later logins with the
  same fingerprint skip the code. If ADT refuses to trust the device, the login still
  succeeds, a warning is logged, and the next login asks for a code again.

## Fingerprint

The `fingerprint` argument is the device fingerprint ADT uses to recognise a trusted
device. It doesn't have to come from a browser: pick a string, trust it once with the
verification code flow above, then reuse the same string for every login. To make one:

```python
from pyadtpulse.util import generate_random_fingerprint

fingerprint = generate_random_fingerprint()  # store it and reuse it
```

A new fingerprint means a new verification code, and adds another trusted device to the
account.

**<ins>Warning:</ins> ADT allows one session per account and fingerprint. If another
connection logs in to the Pulse portal with the same fingerprint, the first connection is
logged out. Use a fingerprint only one client uses, and don't reuse one from a browser you
log in to Pulse with.**

### Using a browser's fingerprint

Before the verification code flow existed, the only way to get a trusted fingerprint was to
trust a browser on the Pulse website and copy that browser's fingerprint. This still works
if you already have one. Either:

1. Open [the fingerprint detector](https://rawcdn.githack.com/homeassistant-projects/pyadtpulse/5fe719d2bea2b6e68aec0588c4d92f363223424d/doc/browser_fingerprint.html)
   ([source](doc/browser_fingerprint.html)) in the browser you trusted, or
2. Follow [homebridge-adt-pulse's instructions](https://github.com/mrjackyliang/homebridge-adt-pulse#configure-2-factor-authentication).

A browser's fingerprint changes when the browser or OS is upgraded, and you then need to
trust it again.

## Options

`PyADTPulseAsync(username, password, fingerprint, ...)` also takes:

| Argument | Default | Meaning |
| --- | --- | --- |
| `service_host` | `"https://portal.adtpulse.com"` | Portal to use. Canadian accounts use `"https://portal-ca.adtpulse.com"` (`pyadtpulse.const.API_HOST_CA`). |
| `user_agent` | a desktop Chrome user agent | User-Agent header sent to ADT. |
| `keepalive_interval` | `5` | Minutes between keepalive requests that keep the session open. Must be from 1 to 15. |
| `relogin_interval` | `120` | Minutes between background re-logins. Each re-login happens at a random point between 75% and 100% of the interval. Must be at least 20. |
| `detailed_debug_logging` | `False` | Log more detail, such as each request and how long updates take. |
| `debug_locks` | `False` | Use locks that log who holds them, for debugging. |

`keepalive_interval`, `relogin_interval` and `detailed_debug_logging` are also properties
you can change on a running client. Setting `keepalive_interval` or `relogin_interval` to
`None` restores the default; a value out of range raises `ValueError`.

```python
adt.keepalive_interval = 10  # minutes
adt.relogin_interval = 60  # minutes
adt.site.gateway.poll_interval = 2.0  # seconds between update checks (the default)
```

`poll_interval` belongs to the site's gateway and is only available after login. When the
gateway goes offline, pyadtpulse backs off from it, up to 10 minutes between checks.

## Upgrading to 2.0

pyadtpulse 2.0 removes code that was deprecated or never worked:

- The synchronous `PyADTPulse` client, along with the sync `ADTPulseSite` methods
  `arm_home()`, `arm_away()`, `disarm()` and `update_zones()`. Use `PyADTPulseAsync`
  and the site's `async_arm_home()`, `async_arm_away()`, `async_arm_night()` and
  `async_disarm()` methods instead.
- `util.generate_fingerprint_from_browser_json()`. Pass the fingerprint string itself
  (see [Fingerprint](#fingerprint)).
- The deprecated `ADTPulseSite` members `updates_may_exist`, `update()`,
  `async_update()` and `site_lock`. `PyADTPulseAsync.wait_for_update()` reports
  updates.
- `ADTPulseZones.update_status()`, `update_state()` and
  `update_last_activity_timestamp()`. Use `update_device_info()`.
- The unused constants `ADT_ZONES_URI`, `ADT_STATES_URI`, `ADT_ARM_URI`, `STATE_OPEN`,
  `STATE_MOTION`, `STATE_TAMPER`, `STATE_ALARM`, `STATE_UNKNOWN` and `ADT_SENSOR_*`.

Other changes:

- `ADTPulseFlattendZone` is renamed `ADTPulseFlattenedZone`.
- `ADTPulseSite.zones` and `zones_as_dict` return an empty list or `ADTPulseZones`
  when the site has no zones, instead of raising `RuntimeError`.

## See Also

- [ADT Pulse Portal](https://portal.adtpulse.com/)
- [Home Assistant ADT Pulse integration](https://github.com/homeassistant-projects/hass-adtpulse)
- [adt-pulse-mqtt](https://github.com/adt-pulse-mqtt/adt-pulse-mqtt) – MQTT integration with ADT Pulse alarm panels

## Future Enhancements

Feature ideas:

- Cameras (via Janus)

Feature ideas, but no plans to implement:

- support OFFLINE status checking
- support multiple sites (premises/locations) under a single ADT account
- alarm history (/ajax/alarmHistory.jsp)
