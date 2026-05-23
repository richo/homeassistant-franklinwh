"""Select platform for FranklinWH — operating mode control."""

from __future__ import annotations

from datetime import timedelta
import logging

import franklinwh
import httpx
import voluptuous as vol

from homeassistant.components.select import (
    PLATFORM_SCHEMA as SELECT_PLATFORM_SCHEMA,
    SelectEntity,
)
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

_LOGGER = logging.getLogger(__name__)
DEFAULT_UPDATE_INTERVAL = 30

DEFAULT_TOU_RESERVE = 20
DEFAULT_SELF_RESERVE = 20
DEFAULT_EMERGENCY_RESERVE = 100

PLATFORM_SCHEMA = SELECT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_ID): cv.string,
        vol.Optional("use_sn", default=False): cv.boolean,
        vol.Optional("prefix", default=False): cv.string,
        vol.Optional(
            "update_interval", default=DEFAULT_UPDATE_INTERVAL
        ): cv.time_period,
        vol.Optional("tou_reserve_pct", default=DEFAULT_TOU_RESERVE): cv.positive_int,
        vol.Optional("self_consumption_reserve_pct", default=DEFAULT_SELF_RESERVE): cv.positive_int,
        vol.Optional("emergency_backup_reserve_pct", default=DEFAULT_EMERGENCY_RESERVE): cv.positive_int,
    }
)

# Human-readable option strings shown in the Home Assistant UI
OPTION_TIME_OF_USE = "Time of Use"
OPTION_SELF_CONSUMPTION = "Self Consumption"
OPTION_EMERGENCY_BACKUP = "Emergency Backup"

MODE_OPTIONS = [OPTION_TIME_OF_USE, OPTION_SELF_CONSUMPTION, OPTION_EMERGENCY_BACKUP]

# franklinwh library internal mode strings (matches franklinwh.client.MODE_*)
# Defined locally so we don't import private symbols not in franklinwh.__all__
_API_TIME_OF_USE = "time_of_use"
_API_SELF_CONSUMPTION = "self_consumption"
_API_EMERGENCY_BACKUP = "emergency_backup"

# Map from the franklinwh library's internal mode strings → UI option strings
_API_TO_OPTION: dict[str, str] = {
    _API_TIME_OF_USE: OPTION_TIME_OF_USE,
    _API_SELF_CONSUMPTION: OPTION_SELF_CONSUMPTION,
    _API_EMERGENCY_BACKUP: OPTION_EMERGENCY_BACKUP,
}

# Map from UI option strings → Mode factory callables
_OPTION_TO_MODE_FACTORY = {
    OPTION_TIME_OF_USE: franklinwh.Mode.time_of_use,
    OPTION_SELF_CONSUMPTION: franklinwh.Mode.self_consumption,
    OPTION_EMERGENCY_BACKUP: franklinwh.Mode.emergency_backup,
}

# Map from get_composite_info() currentWorkMode (1/2/3) → internal mode string.
# Uses the same encoding as Mode.workMode; the runingMode field in
# _switch_status() is not reliable for mode detection across firmware versions.
_WORK_MODE_TO_API: dict[int, str] = {
    1: _API_TIME_OF_USE,
    2: _API_SELF_CONSUMPTION,
    3: _API_EMERGENCY_BACKUP,
}


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the select platform."""
    username: str = config[CONF_USERNAME]
    password: str = config[CONF_PASSWORD]
    gateway: str = config[CONF_ID]
    update_interval: timedelta = config["update_interval"]

    # TODO(richo) why does it string the default value
    if config["use_sn"] and config["use_sn"] != "False":
        unique_id = gateway
    else:
        unique_id = None

    # TODO(richo) why does it string the default value
    if config["prefix"] and config["prefix"] != "False":
        prefix = config["prefix"]
    else:
        prefix = "FranklinWH"

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)

    reserves: dict[str, int] = {
        OPTION_TIME_OF_USE: config["tou_reserve_pct"],
        OPTION_SELF_CONSUMPTION: config["self_consumption_reserve_pct"],
        OPTION_EMERGENCY_BACKUP: config["emergency_backup_reserve_pct"],
    }

    async def _update_data() -> str:
        """Fetch the current operating mode from the gateway."""
        _LOGGER.debug("Fetching operating mode from FranklinWH")

        # Try the library's get_mode() first
        try:
            mode_name, _ = await client.get_mode()
            return mode_name
        except franklinwh.client.DeviceTimeoutException as e:
            raise UpdateFailed(f"Device timeout: {e}") from e
        except franklinwh.client.GatewayOfflineException as e:
            raise UpdateFailed(f"Gateway offline: {e}") from e
        except franklinwh.client.AccountLockedException as e:
            raise UpdateFailed(f"Account locked: {e}") from e
        except franklinwh.client.InvalidCredentialsException as e:
            raise UpdateFailed(f"Invalid credentials: {e}") from e
        except Exception as e:  # noqa: BLE001
            # get_mode() raises KeyError when runingMode is not in MODE_MAP —
            # observed on some firmware versions. Fall through to the fallback.
            _LOGGER.debug(
                "get_mode() raised %s, falling back to composite info",
                type(e).__name__,
            )

        # Fallback: get_composite_info() returns currentWorkMode (1/2/3) using
        # the same encoding as Mode.workMode and is reliable across firmware.
        try:
            composite = await client.get_composite_info()
            work_mode = composite.get("currentWorkMode")
            if work_mode is not None:
                mode_name = _WORK_MODE_TO_API.get(int(work_mode))
                if mode_name is not None:
                    _LOGGER.debug(
                        "currentWorkMode=%s → mode %s", work_mode, mode_name
                    )
                    return mode_name
            raise UpdateFailed(f"Unrecognised currentWorkMode: {work_mode!r}")
        except UpdateFailed:
            raise
        except franklinwh.client.DeviceTimeoutException as e:
            raise UpdateFailed(f"Device timeout: {e}") from e
        except franklinwh.client.GatewayOfflineException as e:
            raise UpdateFailed(f"Gateway offline: {e}") from e
        except Exception as e:  # noqa: BLE001
            raise UpdateFailed(f"Error reading operating mode: {e}") from e

    coordinator = DataUpdateCoordinator[str](
        hass,
        _LOGGER,
        name="franklinwh_mode",
        update_method=_update_data,
        update_interval=update_interval,
        always_update=False,
    )

    # Initial fetch so the entity is available immediately on startup
    await coordinator.async_refresh()

    async_add_entities([OperatingModeSelect(coordinator, prefix, gateway, client, reserves)])


class OperatingModeSelect(
    CoordinatorEntity[DataUpdateCoordinator[str]],
    SelectEntity,
):
    """Select entity exposing the FranklinWH operating mode."""

    _attr_options = MODE_OPTIONS

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        prefix: str,
        gateway: str,
        client: franklinwh.Client,
        reserves: dict[str, int],
    ) -> None:
        """Initializer."""
        super().__init__(coordinator)
        self._attr_name = f"{prefix} Operating Mode"
        self._client = client
        self._attr_unique_id = gateway + "_operating_mode"
        self._reserves = reserves

    @property
    def available(self) -> bool:
        """Is the entity available?"""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently active operating mode."""
        if self.coordinator.data is None:
            return None
        return _API_TO_OPTION.get(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        """Change the operating mode."""
        if option not in _OPTION_TO_MODE_FACTORY:
            _LOGGER.error("Unknown operating mode option: %s", option)
            return

        soc = self._reserves.get(option)
        mode_obj = _OPTION_TO_MODE_FACTORY[option](soc=soc) if soc is not None else _OPTION_TO_MODE_FACTORY[option]()

        _LOGGER.info(
            "Setting FranklinWH operating mode to: %s (reserve=%s%%)", option, soc
        )
        try:
            await self._client.set_mode(mode_obj)
        except httpx.ReadTimeout:
            # The API frequently times out even when the command succeeds.
            # The coordinator refresh below will confirm the actual state.
            _LOGGER.warning(
                "set_mode(%s) timed out — command may still have been applied",
                option,
            )

        # Refresh so the entity state reflects the change immediately
        await self.coordinator.async_refresh()
