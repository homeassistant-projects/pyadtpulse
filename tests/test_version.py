"""Test that the package version has a single source."""

import re
from pathlib import Path

from pyadtpulse.const import __version__


def test_version_matches_pyproject():
    """__version__ is read from the installed metadata, set in pyproject.toml."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    m = re.search(r'^version = "([^"]+)"', pyproject.read_text(), re.MULTILINE)
    assert m is not None
    assert __version__ == m.group(1)
