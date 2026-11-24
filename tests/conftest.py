"""Pulse Test Configuration."""

import os
import re
import sys
from enum import Enum
from typing import Any
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock
from collections.abc import Generator

import pytest
import freezegun
from aiohttp import client_exceptions
from aioresponses import aioresponses

# Get the root directory of your project
project_root = Path(__file__).resolve().parent

# Modify sys.path to include the project root
sys.path.insert(0, str(project_root))
test_file_dir = project_root / "data_files"
# pylint: disable=wrong-import-position
# ruff: noqa: E402
# flake8: noqa: E402
from pyadtpulse.const import (
    ADT_LOGIN_URI,
    ADT_DEVICE_URI,
    ADT_LOGOUT_URI,
    ADT_SYSTEM_URI,
    ADT_GATEWAY_URI,
    ADT_SUMMARY_URI,
    ADT_MFA_FAIL_URI,
    DEFAULT_API_HOST,
)
from pyadtpulse.pulse_connection_properties import PulseConnectionProperties

MOCKED_API_VERSION = "27.0.0-140"


class LoginType(Enum):
    """Login Types."""

    SUCCESS = "signin.html"
    MFA = "mfa.html"
    FAIL = "signin_fail.html"
    LOCKED = "signin_locked.html"
    NOT_SIGNED_IN = "not_signed_in.html"


@pytest.fixture
def read_file():
    """
    Fixture to read a file.

    Args:
        file_name (str): Name of the file to read

    """

    def _read_file(file_name: str) -> str:
        return (test_file_dir / file_name).read_text(encoding="utf-8")

    return _read_file


@pytest.fixture
def mock_sleep(mocker):
    """Fixture to mock asyncio.sleep."""
    return mocker.patch("asyncio.sleep", new_callable=AsyncMock)


@pytest.fixture
def freeze_time_to_now():
    """Fixture to freeze time to now."""
    current_time = datetime.now()
    with freezegun.freeze_time(current_time) as frozen_time:
        yield frozen_time


@pytest.fixture
def get_mocked_connection_properties() -> PulseConnectionProperties:
    """Fixture to get the test connection properties."""
    p = PulseConnectionProperties(DEFAULT_API_HOST)
    p.api_version = MOCKED_API_VERSION
    return p


@pytest.fixture
def mock_server_down():
    """Fixture to mock server down."""
    with aioresponses() as m:
        m.get(
            DEFAULT_API_HOST,
            status=500,
            exception=client_exceptions.ServerConnectionError(),
            repeat=True,
        )
        yield m


@pytest.fixture
def mock_server_temporarily_down(get_mocked_url, read_file):
    """Fixture to mock server temporarily down."""
    with aioresponses() as responses:
        responses.get(
            DEFAULT_API_HOST,
            status=500,
            exception=client_exceptions.ServerConnectionError(),
        )
        responses.get(
            DEFAULT_API_HOST,
            status=500,
            exception=client_exceptions.ServerConnectionError(),
        )
        responses.get(
            DEFAULT_API_HOST,
            status=302,
            headers={"Location": get_mocked_url(ADT_LOGIN_URI)},
        )
        responses.get(
            f"{DEFAULT_API_HOST}/{ADT_LOGIN_URI}",
            status=307,
            headers={"Location": get_mocked_url(ADT_LOGIN_URI)},
            repeat=True,
        )
        responses.get(
            get_mocked_url(ADT_LOGIN_URI),
            body=read_file("signin.html"),
            content_type="text/html",
        )

        yield responses


@pytest.fixture
def get_mocked_url(get_mocked_connection_properties):
    """Fixture to get the test url."""

    def _get_mocked_url(path: str) -> str:
        return get_mocked_connection_properties.make_url(path)

    return _get_mocked_url


@pytest.fixture
def get_mocked_mapped_static_responses(get_mocked_url) -> dict[str, str]:
    """Fixture to get the test mapped responses."""
    return {
        get_mocked_url(ADT_SUMMARY_URI): "summary.html",
        get_mocked_url(ADT_SYSTEM_URI): "system.html",
        get_mocked_url(ADT_GATEWAY_URI): "gateway.html",
        get_mocked_url(ADT_MFA_FAIL_URI): "mfa.html",
    }


@pytest.fixture
def extract_ids_from_data_directory() -> list[str]:
    """Extract the device ids all the device files in the data directory."""
    id_pattern = re.compile(r"device_(\d{1,})\.html")
    ids = set()
    for file_name in os.listdir(test_file_dir):
        match = id_pattern.match(file_name)
        if match:
            ids.add(match.group(1))
    return list(ids)


@pytest.fixture
def mocked_server_responses(
    get_mocked_mapped_static_responses: dict[str, str],
    read_file,
    get_mocked_url,
    extract_ids_from_data_directory: list[str],
) -> Generator[aioresponses, Any]:
    """Fixture to get the test mapped responses."""
    static_responses = get_mocked_mapped_static_responses
    with aioresponses() as responses:
        for url, file_name in static_responses.items():
            responses.get(
                url, body=read_file(file_name), content_type="text/html", repeat=True
            )

            # device id rewriting
        for device_id in extract_ids_from_data_directory:
            responses.get(
                f"{get_mocked_url(ADT_DEVICE_URI)}?id={device_id}",
                body=read_file(f"device_{device_id}.html"),
                content_type="text/html",
            )
        # redirects
        responses.get(
            get_mocked_url(ADT_LOGIN_URI),
            body=read_file("signin.html"),
            content_type="text/html",
        )
        responses.get(
            DEFAULT_API_HOST,
            status=302,
            headers={"Location": get_mocked_url(ADT_LOGIN_URI)},
            repeat=True,
        )
        responses.get(
            f"{DEFAULT_API_HOST}/",
            status=302,
            headers={"Location": get_mocked_url(ADT_LOGIN_URI)},
            repeat=True,
        )
        responses.get(
            f"{DEFAULT_API_HOST}/{ADT_LOGIN_URI}",
            status=307,
            headers={"Location": get_mocked_url(ADT_LOGIN_URI)},
            repeat=True,
        )
        # login/logout

        logout_pattern = re.compile(
            rf"{re.escape(get_mocked_url(ADT_LOGOUT_URI))}/?.*$"
        )
        responses.get(
            logout_pattern,
            status=302,
            headers={"Location": get_mocked_url(ADT_LOGIN_URI)},
            repeat=True,
        )

        # not doing default sync check response or keepalive
        # because we need to set it on each test
        yield responses


def add_custom_response(
    mocked_server_responses,
    read_file,
    url: str,
    method: str = "GET",
    status: int = 200,
    file_name: str | None = None,
    headers: dict[str, Any] | None = None,
):
    """Add a custom response to the mocked server."""
    if method.upper() not in ("GET", "POST"):
        raise ValueError("Unsupported HTTP method. Only GET and POST are supported.")

    mocked_server_responses.add(
        url,
        method,
        status=status,
        body=read_file(file_name) if file_name else "",
        content_type="text/html",
        headers=headers,
    )


def add_signin(
    signin_type: LoginType, mocked_server_responses, get_mocked_url, read_file
):
    """Add a signin response to the mocked server."""
    if signin_type != LoginType.SUCCESS:
        add_custom_response(
            mocked_server_responses,
            read_file,
            get_mocked_url(ADT_LOGIN_URI),
            file_name=signin_type.value,
        )
    redirect = get_mocked_url(ADT_LOGIN_URI)
    if signin_type == LoginType.MFA:
        redirect = get_mocked_url(ADT_MFA_FAIL_URI)
    if signin_type == LoginType.SUCCESS:
        redirect = get_mocked_url(ADT_SUMMARY_URI)
    add_custom_response(
        mocked_server_responses,
        read_file,
        get_mocked_url(ADT_LOGIN_URI),
        status=307,
        method="POST",
        headers={"Location": redirect},
    )


def add_logout(mocked_server_responses, get_mocked_url, read_file):
    """Add a logout response to the mocked server."""
    add_custom_response(
        mocked_server_responses,
        read_file,
        get_mocked_url(ADT_LOGOUT_URI),
        file_name=LoginType.SUCCESS.value,
    )
