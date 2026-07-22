"""FranklinWH integration — shared client, coordinators, and helpers."""

from __future__ import annotations

import logging
import time
from typing import Any

import franklinwh

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

DOMAIN = "franklin_wh"

# Rate limit circuit breaker: when the API returns code 181, stop all
# requests for an exponentially increasing backoff period.  This prevents
# HA's 30-60s retry loops from prolonging an account lockout.
_RATE_LIMIT_KEY = "rate_limit_until"
_RATE_LIMIT_BACKOFF_KEY = "rate_limit_backoff"
_INITIAL_BACKOFF_SECONDS = 120  # 2 minutes
_MAX_BACKOFF_SECONDS = 1800  # 30 minutes


def check_rate_limit(hass: HomeAssistant) -> None:
    """Raise UpdateFailed if we're in a rate-limit backoff period.

    Call this at the top of every coordinator _update_data() function.
    """
    data = hass.data.get(DOMAIN, {})
    until = data.get(_RATE_LIMIT_KEY, 0)
    if time.time() < until:
        remaining = int(until - time.time())
        raise UpdateFailed(
            f"FranklinWH API rate limited — backing off for {remaining}s. "
            f"Check the Franklin app if this persists."
        )


def handle_rate_limit(hass: HomeAssistant) -> None:
    """Activate the rate-limit circuit breaker with exponential backoff.

    Call this when any API call returns code 181 or AccountLockedException.
    """
    hass.data.setdefault(DOMAIN, {})
    current_backoff = hass.data[DOMAIN].get(_RATE_LIMIT_BACKOFF_KEY, _INITIAL_BACKOFF_SECONDS)
    hass.data[DOMAIN][_RATE_LIMIT_KEY] = time.time() + current_backoff
    hass.data[DOMAIN][_RATE_LIMIT_BACKOFF_KEY] = min(current_backoff * 2, _MAX_BACKOFF_SECONDS)
    _LOGGER.warning(
        "FranklinWH API rate limited (code 181). "
        "Pausing ALL API calls for %s seconds to let the lockout expire. "
        "Next backoff will be %ss if it happens again.",
        current_backoff,
        min(current_backoff * 2, _MAX_BACKOFF_SECONDS),
    )


def clear_rate_limit(hass: HomeAssistant) -> None:
    """Reset the backoff after a successful API call."""
    data = hass.data.get(DOMAIN, {})
    if _RATE_LIMIT_KEY in data:
        _LOGGER.info("FranklinWH API recovered from rate limit")
        data.pop(_RATE_LIMIT_KEY, None)
        data[_RATE_LIMIT_BACKOFF_KEY] = _INITIAL_BACKOFF_SECONDS


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the FranklinWH integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


def get_shared_client(
    hass: HomeAssistant,
    username: str,
    password: str,
    gateway: str,
) -> franklinwh.Client:
    """Return a shared FranklinWH Client for the given gateway.

    All platforms (sensor, switch, select, number) should call this instead
    of creating their own Client.  The Client and its TokenFetcher are
    cached in ``hass.data`` keyed by gateway serial so that a single auth
    session is reused across platforms.
    """
    hass.data.setdefault(DOMAIN, {})
    key = f"client_{gateway}"

    if key not in hass.data[DOMAIN]:
        _LOGGER.debug("Creating shared FranklinWH client for gateway %s", gateway)
        fetcher = franklinwh.TokenFetcher(username, password)
        client = franklinwh.Client(fetcher, gateway)
        hass.data[DOMAIN][key] = client

    return hass.data[DOMAIN][key]


def get_shared_coordinator(
    hass: HomeAssistant,
    gateway: str,
    name: str,
) -> DataUpdateCoordinator[dict[str, Any]] | None:
    """Retrieve a shared coordinator stored by another platform.

    Returns None if the coordinator hasn't been created yet.
    """
    return hass.data.get(DOMAIN, {}).get(f"coordinator_{gateway}_{name}")


def set_shared_coordinator(
    hass: HomeAssistant,
    gateway: str,
    name: str,
    coordinator: DataUpdateCoordinator[dict[str, Any]],
) -> None:
    """Store a coordinator for sharing across platforms."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][f"coordinator_{gateway}_{name}"] = coordinator
