# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pyadtpulse is a Python async library that provides an interface to ADT Pulse security systems. It supports both synchronous and asynchronous operations, with the async version (`PyADTPulseAsync`) being the preferred implementation.

## Core Architecture

### Main Components

- **PyADTPulse/PyADTPulseAsync**: Main client classes in `pyadtpulse_async.py` and `__init__.py`
- **PulseConnection**: HTTP session management and connection handling in `pulse_connection.py`
- **ADTPulseSite**: Represents individual ADT sites/locations in `site.py`
- **ADTZone**: Individual security zones (doors, windows, motion sensors) in `zones.py`
- **Authentication**: Login handling and session management in `pulse_authentication_properties.py`

### Key Design Patterns

- **Async-first architecture**: All core operations are async with sync wrappers
- **Connection pooling**: Reuses HTTP sessions and manages authentication state
- **Background tasks**: Automatic keepalive, relogin, and sync checking
- **Thread safety**: Uses locks for sync/async coordination

## Development Commands

### Code Quality
- **Linting**: `ruff check` and `ruff format` (configured in pyproject.toml)
- **Type checking**: `mypy` (configured in pyproject.toml)
- **Pre-commit hooks**: `pre-commit run --all-files` (see .pre-commit-config.yaml)

### Testing
- **Run all tests**: `python -m pytest`
- **Run specific test**: `python -m pytest tests/test_filename.py`
- **Run with coverage**: `python -m pytest --cov=pyadtpulse --cov-report=html`
- **Test timeout**: 30 seconds (configured in pyproject.toml)

### Package Management
- Uses Poetry for dependency management
- **Install dependencies**: `poetry install`
- **Add dependency**: `poetry add package_name`
- **Update dependencies**: `poetry update`

## Important Implementation Notes

### Authentication & Sessions
- ADT Pulse requires browser fingerprinting for 2FA bypass
- Sessions are automatically managed with keepalive and relogin intervals
- Multiple concurrent sessions with same credentials will cause logouts

### Async/Sync Coordination
- `PyADTPulse` (sync) is deprecated - use `PyADTPulseAsync` for new code
- Background thread management in sync version handles async operations
- All API calls go through async methods internally

### Error Handling
- Custom exceptions in `exceptions.py` for different failure modes
- Backoff/retry logic in `pulse_backoff.py`
- Connection status tracking in `pulse_connection_status.py`

### Testing Strategy
- Test data files in `tests/data_files/` contain HTML responses
- Mock HTTP responses using `aioresponses`
- Async test fixtures in `conftest.py`

## Common Patterns

### Adding New Features
1. Implement async version first in appropriate module
2. Add tests with mock data files
3. Update sync wrapper if needed
4. Follow existing error handling patterns

### API Endpoints
- All ADT Pulse endpoints are accessed through `PulseConnection`
- Base URL configurable via `service_host` parameter
- Response parsing typically uses lxml for HTML parsing

### Background Tasks
- Sync check task monitors for data updates
- Keepalive prevents session timeout
- Relogin handles authentication refresh
- All managed through asyncio task scheduling