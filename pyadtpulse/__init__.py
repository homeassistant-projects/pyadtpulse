"""Async Python client for ADT Pulse."""

import aiohttp_fast_zlib

from .pyadtpulse_async import PyADTPulseAsync

aiohttp_fast_zlib.enable()

__all__ = ["PyADTPulseAsync"]
