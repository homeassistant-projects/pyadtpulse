## 1.2.12 (2025-10-14)
# What's Changed
* Bump freezegun from 1.5.3 to 1.5.5 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/56
* Bump pre-commit from 4.2.0 to 4.3.0 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/55
* Bump aiohttp from 3.12.14 to 3.12.15 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/54
* Bump pytest-asyncio from 1.0.0 to 1.1.0 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/52
* Bump ruff from 0.12.3 to 0.12.8 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/51
* Bump build from 1.2.2.post1 to 1.3.0 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/53
* Pypi publish fix by @EVWorth in https://github.com/homeassistant-projects/pyadtpulse/pull/58
* Bump ruff from 0.12.8 to 0.12.10 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/61
* Bump lxml from 6.0.0 to 6.0.1 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/62
* Bump ruff from 0.12.10 to 0.12.11 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/63
* Bump pytest from 8.4.1 to 8.4.2 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/65
* Bump ruff from 0.12.11 to 0.12.12 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/66
* Bump pytest-mock from 3.14.1 to 3.15.0 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/67
* Bump twine from 6.1.0 to 6.2.0 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/64
* Bump pytest-isolate from 0.0.12 to 0.0.13 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/68
* Bump ruff from 0.12.12 to 0.13.0 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/69
* Bump pytest-asyncio from 1.1.0 to 1.2.0 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/70
* Bump ruff from 0.13.0 to 0.13.3 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/75
* Bump lxml from 6.0.1 to 6.0.2 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/72
* Bump pytest-mock from 3.15.0 to 3.15.1 by @dependabot[bot] in https://github.com/homeassistant-projects/pyadtpulse/pull/71
* Ruff formatting, pre-commit, and validate workflow by @EVWorth in https://github.com/homeassistant-projects/pyadtpulse/pull/50

# New Contributors
* @dependabot[bot] made their first contribution in https://github.com/homeassistant-projects/pyadtpulse/pull/56

**Full Changelog**: https://github.com/homeassistant-projects/pyadtpulse/compare/1.2.11...1.2.12

## 1.2.11 (2025-07-12)
# What's Changed
* Refactor for uv by @EVWorth in https://github.com/homeassistant-projects/pyadtpulse/pull/45
* Update aiohttp zlib ng to aiohttp fast zlib zlib ng  by @EVWorth in https://github.com/homeassistant-projects/pyadtpulse/pull/47
* Workflow improvements by @EVWorth in https://github.com/homeassistant-projects/pyadtpulse/pull/48
* Unit test fixes/removals by @HeroesDieYoung in https://github.com/homeassistant-projects/pyadtpulse/pull/42

# New Contributors
* @EVWorth made their first contribution in https://github.com/homeassistant-projects/pyadtpulse/pull/45

**Full Changelog**: https://github.com/homeassistant-projects/pyadtpulse/compare/1.2.10...1.2.11

## 1.2.9 (2024-04-21)

* ignore query string in check_login_errors().  This should fix a bug where the task was logged out
  but not correctly being identified
* remove unnecessary warning in alarm status check
* add arm night
* refactor update_alarm_from_etree()
* bump to newer user agent
* skip sync check if it will back off
* fix linter issue in _initialize_sites

## 1.2.8 (2024-03-07)

* add more detail to "invalid sync check" error logging
* don't exit sync check task on service temporarily unavailable or invalid login
* don't use empty site id for logins

## 1.2.7 (2024-02-23)

* catch site is None on logout to prevent "have you logged in" errors
* speed improvements via aiohttp-zlib-ng

## 1.2.6 (2024-02-23)

Performance improvements including:

* switch from BeautifulSoup to lxml for faster parsing
* optimize zone parsing to only update zones which have changed
* change wait_for_update() to pass the changed zones/alarm state to caller

## 1.2.5 (2024-02-10)

* don't raise not logged in exception when sync check task logs out
* change full logout interval to approximately every 6 hours

## 1.2.4 (2024-02-08)

* change yarl dependencies

## 1.2.3 (2024-02-08)

* change aiohttp dependencies

## 1.2.2 (2024-02-07)

* add yarl as dependency

## 1.2.1 (2024-02-07)

* add timing loggin for zone/site updates
* do full logout once per day
* have keepalive task wait for sync check task to sleep before logging out

## 1.2.0 (2024-01-30)

* add exceptions and exception handling
* make code more robust for error handling
* refactor code into smaller objects
* add testing framework
* add poetry

## 1.1.5 (2023-12-22)

* fix more zone html parsing due to changes in Pulse v27

## 1.1.4 (2023-12-13)

* fix zone html parsing due to changes in Pulse v27

## 1.1.3 (2023-10-11)

* revert sync check logic to check against last check value.  this should hopefully fix the problem of HA alarm status not updating
* use exponential backoff for gateway updates if offline instead of constant 90 seconds
* add jitter to relogin interval
* add quick_relogin/async_quick_relogin to do a quick relogin without requerying devices, exiting tasks
* add more alarm testing in example client

## 1.1.2 (2023-10-06)

* change default poll interval to 2 seconds
* update pyproject.toml
* change source location to github/rlippmann from github/rsnodgrass
* fix gateway attributes not updating
* remove dependency on python_dateutils
* add timestamp to example-client logging

## 1.1.1 (2023-10-02)

* pylint fixes
* set min relogin interval
* set max keepalive interval
* remove poll_interval from pyADTPulse constructor
* expose public methods in ADTPulseConnection object

## 1.1 (2023-09-20)

* bug fixes
* relogin support
* device dataclasses

## 1.0 (2023-03-28)

* async support
* background refresh
* bug fixes

## 0.1.0 (2019-12-16)

* added ability to override the ADT API host (example: Canada endpoint portal-ca.adtpulse.com)

## 0.0.6 (2019-09-23)

* bug fixes and improvements

## 0.0.1 (2019-09-19)

* initial release with minimal error/failure handling
