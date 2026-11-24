"""Test logging in through the Pulse MFA challenge."""

import json
import time
import asyncio
import logging

import pytest
from yarl import URL

from tests.conftest import LoginType, add_signin, add_custom_response
from pyadtpulse.const import (
    ADT_LOGIN_URI,
    ADT_SYSTEM_URI,
    ADT_SUMMARY_URI,
    ADT_MFA_FAIL_URI,
    DEFAULT_API_HOST,
)
from pyadtpulse.pulse_mfa import (
    ADT_MFA_STATE_HREF,
    ADT_POST_SIGNIN_URI,
    PulseMFAChallenge,
)
from pyadtpulse.exceptions import (
    PulseConnectionError,
    PulseMFARequiredError,
    PulseNotLoggedInError,
    PulseAuthenticationError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
)
from tests.test_pulse_connection import setup_pulse_connection

# values in tests/data_files/mfa.html
FIXTURE_LOGIN = "robert.lippmann.development@gmail.com"
FIXTURE_SAT = "48f4fa5b-dc92-4a3e-a781-b95fa24a8725"

REQUEST_OTP_HREF = "rest/adt/ui/client/multiFactorAuth/requestOtpForRegisteredProperty"
VALIDATE_OTP_HREF = "rest/adt/ui/client/multiFactorAuth/validateOtp"
TRUST_HREF = "rest/adt/ui/client/multiFactorAuth/addTrustedDevice"
X_TOKEN = "u=user%40example.com&iss=1&exp=2&own=site&ake=key&acl=all&sig=abc%3D"

MFA_STATE = {
    "state": {
        "mfaEnabled": True,
        "mfaProperties": [{"id": "EMAIL", "type": "EMAIL", "label": "u***@e***.com"}],
    },
    "commands": {
        "requestOtpForRegisteredProperty": {
            "params": {
                "id": {
                    "options": [{"value": "EMAIL", "type": "EMAIL"}],
                    "type": "select",
                }
            },
            "method": "POST",
            "action": REQUEST_OTP_HREF,
        },
        "validateOtp": {
            "params": {"otp": {"type": "textInput"}},
            "method": "POST",
            "action": VALIDATE_OTP_HREF,
        },
    },
}


def test_challenge_from_mfa_page(read_file):
    """The challenge is parsed from the MFA page and its token kept out of repr."""
    challenge = PulseMFAChallenge.from_page(read_file("mfa.html"))
    assert challenge is not None
    assert challenge.login == FIXTURE_LOGIN
    assert challenge.sat == FIXTURE_SAT
    assert challenge.proxy_uri == "/nga/serv/RunRRAProxy"
    assert challenge.pre_auth_token.startswith("921F1D19")
    assert challenge.pre_auth_token not in repr(challenge)
    assert challenge.headers()["X-preAuthToken"] == challenge.pre_auth_token
    assert "X-preAuthToken" not in challenge.headers("token")
    assert PulseMFAChallenge.from_page(read_file("signin.html")) is None


def _proxy(get_mocked_url, href: str) -> str:
    return get_mocked_url(f"/nga/serv/RunRRAProxy?href={href}&sat={FIXTURE_SAT}")


def _add_json(mocked, read_file, url, body, method="GET"):
    mocked.add(url, method, status=200, body=json.dumps(body), repeat=False)


def _sent(mocked, method, url):
    return mocked.requests[(method, URL(url))]


async def _login_until_mfa(pc, mocked, get_mocked_url, read_file):
    add_signin(LoginType.MFA, mocked, get_mocked_url, read_file)
    with pytest.raises(PulseMFARequiredError) as exc:
        await pc.async_do_login_query()
    return exc.value


@pytest.mark.asyncio
async def test_mfa_login(mocked_server_responses, get_mocked_url, read_file):
    """A login that needs MFA finishes with a code and trusts the device."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    exc = await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    assert exc.challenge is not None
    assert not pc.is_connected

    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, REQUEST_OTP_HREF),
        {"code": 0, "detail": "OK"},
        method="POST",
    )
    assert await pc.async_request_mfa_code() == "EMAIL"
    sent = _sent(mocked, "POST", _proxy(get_mocked_url, REQUEST_OTP_HREF))
    assert sent[0].kwargs["data"] == {"id": "EMAIL"}
    assert sent[0].kwargs["headers"]["X-login"] == FIXTURE_LOGIN
    assert "X-preAuthToken" in sent[0].kwargs["headers"]

    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        {"code": 0, "detail": X_TOKEN},
        method="POST",
    )
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, TRUST_HREF),
        {"code": 0, "detail": "OK"},
        method="POST",
    )
    add_custom_response(
        mocked,
        read_file,
        get_mocked_url(ADT_POST_SIGNIN_URI),
        status=302,
        headers={"Location": get_mocked_url(ADT_SUMMARY_URI)},
    )
    tree = await pc.async_submit_mfa_code(" 123456 ", "Home Assistant")
    assert tree is not None
    assert pc.is_connected

    validated = _sent(mocked, "POST", _proxy(get_mocked_url, VALIDATE_OTP_HREF))
    assert validated[0].kwargs["data"] == {"otp": "123456"}
    trusted = _sent(mocked, "POST", _proxy(get_mocked_url, TRUST_HREF))
    assert trusted[0].kwargs["data"] == {"name": "Home%20Assistant"}
    assert trusted[0].kwargs["headers"]["X-token"] == X_TOKEN
    assert "X-preAuthToken" not in trusted[0].kwargs["headers"]


@pytest.mark.asyncio
async def test_mfa_wrong_code(mocked_server_responses, get_mocked_url, read_file):
    """A rejected code raises PulseAuthenticationError and leaves us logged out."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    # what Pulse sends for a wrong code
    mocked.add(
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        "POST",
        status=400,
        body=json.dumps(
            {
                "code": 400,
                "detail": "Invalid code. Please re-enter or request a new code",
            }
        ),
    )
    with pytest.raises(PulseAuthenticationError):
        await pc.async_submit_mfa_code("000000")
    assert not pc.is_connected
    # a wrong code is not a connection problem
    assert pc._connection_status.get_backoff().backoff_count == 0


@pytest.mark.asyncio
async def test_mfa_code_not_sent(mocked_server_responses, get_mocked_url, read_file):
    """A code request Pulse does not answer with OK raises."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, REQUEST_OTP_HREF),
        {"code": 1, "detail": "Too many requests"},
        method="POST",
    )
    with pytest.raises(PulseAuthenticationError):
        await pc.async_request_mfa_code()


@pytest.mark.asyncio
async def test_mfa_on_other_api_version(
    mocked_server_responses, get_mocked_url, read_file
):
    """MFA calls go to the API version the sign-in landed on."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    other = "31.0.0-39"
    mfa_page = f"{DEFAULT_API_HOST}/myhome/{other}{ADT_MFA_FAIL_URI}"
    add_custom_response(
        mocked,
        read_file,
        get_mocked_url(ADT_LOGIN_URI),
        method="POST",
        status=307,
        headers={"Location": mfa_page},
    )
    add_custom_response(mocked, read_file, mfa_page, file_name="mfa.html")
    with pytest.raises(PulseMFARequiredError):
        await pc.async_do_login_query()
    state_url = (
        f"{DEFAULT_API_HOST}/myhome/{other}/nga/serv/RunRRAProxy"
        f"?href={ADT_MFA_STATE_HREF}&sat={FIXTURE_SAT}"
    )
    _add_json(mocked, read_file, state_url, MFA_STATE)
    request_url = state_url.replace(ADT_MFA_STATE_HREF, REQUEST_OTP_HREF)
    _add_json(mocked, read_file, request_url, {"code": 0, "detail": "OK"}, "POST")
    assert await pc.async_request_mfa_code() == "EMAIL"


@pytest.mark.asyncio
async def test_mfa_login_when_trust_fails(
    mocked_server_responses, get_mocked_url, read_file
):
    """A failed trust request does not undo a login whose code was accepted."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        {"code": 0, "detail": X_TOKEN},
        method="POST",
    )
    mocked.add(_proxy(get_mocked_url, TRUST_HREF), "POST", status=500, body="")
    add_custom_response(
        mocked,
        read_file,
        get_mocked_url(ADT_POST_SIGNIN_URI),
        status=302,
        headers={"Location": get_mocked_url(ADT_SUMMARY_URI)},
    )
    assert await pc.async_submit_mfa_code("123456") is not None
    assert pc.is_connected


@pytest.mark.asyncio
async def test_mfa_trust_name_taken(mocked_server_responses, get_mocked_url, read_file):
    """A device name already used in the account is retried with a suffix."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        {"code": 0, "detail": X_TOKEN},
        method="POST",
    )
    # what Pulse sends when the name is already a trusted device
    taken = {"code": 409, "detail": "That name is taken. Please enter a unique name."}
    mocked.add(
        _proxy(get_mocked_url, TRUST_HREF), "POST", status=409, body=json.dumps(taken)
    )
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, TRUST_HREF),
        {"code": 0, "detail": "OK"},
        method="POST",
    )
    add_custom_response(
        mocked,
        read_file,
        get_mocked_url(ADT_POST_SIGNIN_URI),
        status=302,
        headers={"Location": get_mocked_url(ADT_SUMMARY_URI)},
    )
    assert await pc.async_submit_mfa_code("123456", "Home Assistant") is not None
    names = [
        c.kwargs["data"]["name"]
        for c in _sent(mocked, "POST", _proxy(get_mocked_url, TRUST_HREF))
    ]
    assert names[0] == "Home%20Assistant"
    assert len(names) == 2
    assert names[1].startswith("Home%20Assistant%20")
    assert len(names[1]) == len("Home%20Assistant%20") + 4


@pytest.mark.asyncio
async def test_mfa_gateway_error_is_not_a_wrong_code(
    mocked_server_responses, get_mocked_url, read_file
):
    """A non-JSON error page while validating is a server error, not a bad code."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    mocked.add(
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        "POST",
        status=502,
        body="<html><body>Bad Gateway</body></html>",
        content_type="text/html",
    )
    with pytest.raises(PulseServerConnectionError):
        await pc.async_submit_mfa_code("123456")


@pytest.mark.asyncio
async def test_mfa_login_when_trust_times_out(
    mocked_server_responses, get_mocked_url, read_file
):
    """A trust request that times out does not undo the login."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        {"code": 0, "detail": X_TOKEN},
        method="POST",
    )
    mocked.add(
        _proxy(get_mocked_url, TRUST_HREF), "POST", exception=asyncio.TimeoutError()
    )
    add_custom_response(
        mocked,
        read_file,
        get_mocked_url(ADT_POST_SIGNIN_URI),
        status=302,
        headers={"Location": get_mocked_url(ADT_SUMMARY_URI)},
    )
    assert await pc.async_submit_mfa_code("123456") is not None
    assert pc.is_connected


@pytest.mark.asyncio
async def test_mfa_retry_after_accepted_code_starts_over(
    mocked_server_responses, get_mocked_url, read_file
):
    """Once a code is accepted, a retry needs a new login, not the old challenge."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        {"code": 0, "detail": X_TOKEN},
        method="POST",
    )
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, TRUST_HREF),
        {"code": 0, "detail": "OK"},
        method="POST",
    )
    # the page after the code is not the summary
    add_custom_response(
        mocked,
        read_file,
        get_mocked_url(ADT_POST_SIGNIN_URI),
        status=302,
        headers={"Location": get_mocked_url(ADT_SYSTEM_URI)},
    )
    # the code was accepted, so this is not reported as a wrong code
    with pytest.raises(PulseNotLoggedInError):
        await pc.async_submit_mfa_code("123456")
    with pytest.raises(PulseNotLoggedInError):
        await pc.async_submit_mfa_code("123456")


@pytest.mark.parametrize("status", [500, 503])
@pytest.mark.asyncio
async def test_mfa_server_error_with_json_is_not_a_wrong_code(
    mocked_server_responses, get_mocked_url, read_file, status
):
    """An HTTP 5xx with a JSON body while validating is a server error."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    mocked.add(
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        "POST",
        status=status,
        body=json.dumps({"code": status, "detail": "Internal error"}),
    )
    with pytest.raises(PulseConnectionError) as exc:
        await pc.async_submit_mfa_code("123456")
    assert not isinstance(exc.value, PulseAuthenticationError)


@pytest.mark.asyncio
async def test_mfa_rate_limited_code_request(
    mocked_server_responses, get_mocked_url, read_file
):
    """An HTTP 429 with a JSON body is a rate limit, not a refusal."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    mocked.add(
        _proxy(get_mocked_url, REQUEST_OTP_HREF),
        "POST",
        status=429,
        body=json.dumps({"code": 429, "detail": "Too many requests"}),
    )
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await pc.async_request_mfa_code()


@pytest.mark.asyncio
async def test_mfa_retry_after_is_honored_and_code_not_resent(
    mocked_server_responses, get_mocked_url, read_file
):
    """A 503 with Retry-After is reported with its time, and nothing is resent."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    mocked.add(
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        "POST",
        status=503,
        headers={"Retry-After": "120"},
        body=json.dumps({"code": 503, "detail": "Service unavailable"}),
    )
    before = time.time()
    with pytest.raises(PulseServiceTemporarilyUnavailableError) as exc:
        await pc.async_submit_mfa_code("123456")
    assert exc.value.retry_time is not None
    assert exc.value.retry_time >= int(before) + 120
    # the OTP was sent once, not retried
    assert len(_sent(mocked, "POST", _proxy(get_mocked_url, VALIDATE_OTP_HREF))) == 1
    # until the Retry-After time, nothing more is sent
    with pytest.raises(PulseServiceTemporarilyUnavailableError):
        await pc.async_submit_mfa_code("123456")
    assert len(_sent(mocked, "GET", _proxy(get_mocked_url, ADT_MFA_STATE_HREF))) == 1


@pytest.mark.asyncio
async def test_mfa_login_when_trust_is_unavailable(
    mocked_server_responses, get_mocked_url, read_file
):
    """A trust request answered with HTTP 503 does not undo the login."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        {"code": 0, "detail": X_TOKEN},
        method="POST",
    )
    mocked.add(
        _proxy(get_mocked_url, TRUST_HREF),
        "POST",
        status=503,
        body=json.dumps({"code": 503, "detail": "Service unavailable"}),
    )
    add_custom_response(
        mocked,
        read_file,
        get_mocked_url(ADT_POST_SIGNIN_URI),
        status=302,
        headers={"Location": get_mocked_url(ADT_SUMMARY_URI)},
    )
    assert await pc.async_submit_mfa_code("123456") is not None
    assert pc.is_connected


def test_proxy_url_is_encoded():
    """The proxy URL encodes its query values, and keeps the current format."""
    challenge = PulseMFAChallenge(pre_auth_token="t", login="l", sat=FIXTURE_SAT)
    assert challenge.proxy_url(ADT_MFA_STATE_HREF) == (
        f"/nga/serv/RunRRAProxy?href={ADT_MFA_STATE_HREF}&sat={FIXTURE_SAT}"
    )
    odd = PulseMFAChallenge(pre_auth_token="t", login="l", sat="a&b=c d+e")
    query = URL(odd.proxy_url("rest/x?y=1&z")).query
    assert query["href"] == "rest/x?y=1&z"
    assert query["sat"] == "a&b=c d+e"


@pytest.mark.asyncio
async def test_mfa_rejected_code_logs_reply_without_otp(
    mocked_server_responses, get_mocked_url, read_file, caplog
):
    """A code Pulse does not accept logs what came back, without the OTP."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    exc = await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    pre_auth_token = exc.challenge.pre_auth_token
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        {"code": 7, "detail": "Code 987654 expired", "echo": pre_auth_token},
        method="POST",
    )
    with caplog.at_level(logging.ERROR), pytest.raises(PulseAuthenticationError):
        await pc.async_submit_mfa_code("987654")
    assert "expired" in caplog.text
    assert "987654" not in caplog.text
    assert pre_auth_token not in caplog.text


@pytest.mark.asyncio
async def test_mfa_code_not_sent_logs_reply_without_token(
    mocked_server_responses, get_mocked_url, read_file, caplog
):
    """A code request Pulse does not confirm logs the reply, without the token."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    exc = await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    pre_auth_token = exc.challenge.pre_auth_token
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, REQUEST_OTP_HREF),
        {"code": 1, "detail": "Not sent", "preAuthToken": pre_auth_token},
        method="POST",
    )
    with caplog.at_level(logging.ERROR), pytest.raises(PulseAuthenticationError):
        await pc.async_request_mfa_code()
    assert "Not sent" in caplog.text
    assert pre_auth_token not in caplog.text


@pytest.mark.asyncio
async def test_mfa_trust_refused_logs_reply_without_token(
    mocked_server_responses, get_mocked_url, read_file, caplog
):
    """A trust request Pulse does not confirm logs the reply, without the X-token."""
    mocked = mocked_server_responses
    pc = setup_pulse_connection()
    await _login_until_mfa(pc, mocked, get_mocked_url, read_file)
    _add_json(mocked, read_file, _proxy(get_mocked_url, ADT_MFA_STATE_HREF), MFA_STATE)
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, VALIDATE_OTP_HREF),
        {"code": 0, "detail": X_TOKEN},
        method="POST",
    )
    _add_json(
        mocked,
        read_file,
        _proxy(get_mocked_url, TRUST_HREF),
        {"code": 3, "detail": "Device limit reached", "token": X_TOKEN},
        method="POST",
    )
    add_custom_response(
        mocked,
        read_file,
        get_mocked_url(ADT_POST_SIGNIN_URI),
        status=302,
        headers={"Location": get_mocked_url(ADT_SUMMARY_URI)},
    )
    with caplog.at_level(logging.WARNING):
        assert await pc.async_submit_mfa_code("123456") is not None
    assert "Device limit reached" in caplog.text
    assert X_TOKEN not in caplog.text
    assert "sig=" not in caplog.text
