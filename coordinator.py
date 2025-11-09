"""Coordinator for FranklinWH integration."""

import asyncio
from dataclasses import dataclass, fields
from datetime import timedelta
import logging
from typing import Final

from franklinwh import Client, Stats

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_LOCAL_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN


@dataclass
class FranklinWHData:
    """Statistics for FranklinWH."""

    stats: Stats | None = None
    switch_state: tuple[bool, bool, bool] | None = None


class FranklinWHCoordinator(DataUpdateCoordinator[FranklinWHData]):
    """Fetch FranklinWH data.

    This class always produces stats and optionally other attributes when enabled.
    """

    _data: Final = {
        "stats": "get_stats",
        "switch_state": "get_smart_switch_state",
    }
    attrs: Final = [field.name for field in fields(FranklinWHData)]
    assert len(_data) == len(attrs)

    @staticmethod
    async def disabled() -> None:
        """Placeholder for disabled method."""
        return

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        use_local_api: bool = False,
        local_host: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.use_local_api = use_local_api
        self.local_host = local_host

        # Track consecutive failures
        self._consecutive_failures = 0
        self._max_failures = 3

        self._methods = [self.disabled for _ in self.attrs]
        self.enable("stats")

        # Set update interval based on API type
        update_interval = (
            DEFAULT_LOCAL_SCAN_INTERVAL if use_local_api else DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass,
            logging.getLogger(DOMAIN),
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> FranklinWHData:
        """Fetch data from FranklinWH API."""
        try:
            # Fetch data attributes
            tasks = [function() for function in self._methods]
            results = await asyncio.gather(*tasks)

            # Reset failure counter on success
            self._consecutive_failures = 0

            return FranklinWHData(*results)

        except Exception as err:
            text = str(err).lower()
            # Check if it's an authentication-related error
            if "auth" in text or "token" in text:
                raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

            # Increment failure counter
            self._consecutive_failures += 1
            self.logger.warning(
                "API error (attempt %d/%d): %s",
                self._consecutive_failures,
                self._max_failures,
                err,
            )

            # Only raise UpdateFailed after max failures
            if self._consecutive_failures >= self._max_failures:
                self.logger.error(
                    "Max consecutive failures reached, marking unavailable"
                )
                raise UpdateFailed(f"Error communicating with API: {err}") from err

            # Return last known data to keep entities available
            if self.data:
                self.logger.debug("Returning last known data due to temporary failure")
                return self.data
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def enable(self, attr: str) -> None:
        """Produce an attribute during data fetch."""
        for i, a in enumerate(self.attrs):
            if a == attr:
                self._methods[i] = getattr(self.client, self._data[attr])

    async def async_set_switch_state(self, switches: tuple[bool, bool, bool]) -> None:
        """Set the state of smart switches."""
        try:
            await self.client.set_smart_switch_state(switches)
            # Request immediate refresh
            await self.async_request_refresh()
        except Exception as err:
            self.logger.error("Failed to set switch state: %s", err)
            raise
