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
from homeassistant.core import HomeAssistant, callback
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

# Reverse mapping: UI option string → workMode int (for reserve lookups)
_OPTION_TO_WORK_MODE: dict[str, int] = {
    OPTION_TIME_OF_USE: 1,
    OPTION_SELF_CONSUMPTION: 2,
    OPTION_EMERGENCY_BACKUP: 3,
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
    if config["prefix"] and config["prefix"] != "False":
        prefix = config["prefix"]
    else:
        prefix = "FranklinWH"

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)

    # Seed last-known reserves from config-supplied values (workMode int keys).
    # After the first successful API fetch these are overwritten with live
    # gateway data and carried forward across fallback-path polls, so
    # async_select_option() always uses the most-recently-confirmed reserve
    # rather than reverting to a stale YAML default.
    _last_known_reserves: dict[int, int] = {
        1: config["tou_reserve_pct"],
        2: config["self_consumption_reserve_pct"],
        3: config["emergency_backup_reserve_pct"],
    }

    async def _update_data() -> dict:
        """Fetch operating mode and per-mode reserve SOC from the gateway.

        Returns ``{"mode": <api_mode_str>, "reserves": {workMode: soc, ...}}``.
        On the fallback path the reserves key carries the last successfully
        fetched values so async_select_option() always has consistent SOC data.
        """
        _LOGGER.debug("Fetching operating mode from FranklinWH")

        # Primary: getGatewayTouListV2 returns both the current mode and the
        # per-mode reserve SOC percentages stored on the gateway.  Inlined here
        # so it works with older franklinwh PyPI versions that predate
        # client.get_tou_list().
        async def _get_tou_list():
            url = client.url_base + "hes-gateway/terminal/tou/getGatewayTouListV2"
            result = (await client._post(url, "", params={"showType": "1"}))["result"]
            current_id = result["currendId"]
            res: dict[int, float] = {}
            current_wm: int | None = None
            for entry in result["list"]:
                res[entry["workMode"]] = entry["soc"]
                if entry["id"] == current_id:
                    current_wm = entry["workMode"]
            return {"reserves": res, "current_work_mode": current_wm}

        try:
            tou = await _get_tou_list()
            work_mode = tou.get("current_work_mode")
            if work_mode is not None:
                mode_name = _WORK_MODE_TO_API.get(int(work_mode))
                if mode_name is not None:
                    # Persist the freshly-fetched reserves so they survive a
                    # later fallback-path poll.
                    for wm_int, soc in tou.get("reserves", {}).items():
                        _last_known_reserves[int(wm_int)] = int(soc)
                    _LOGGER.debug(
                        "get_tou_list(): workMode=%s → %s, reserves=%s",
                        work_mode,
                        mode_name,
                        _last_known_reserves,
                    )
                    return {"mode": mode_name, "reserves": dict(_last_known_reserves)}
            raise UpdateFailed(f"Unrecognised current_work_mode: {work_mode!r}")
        except UpdateFailed:
            raise
        except franklinwh.client.DeviceTimeoutException as e:
            raise UpdateFailed(f"Device timeout: {e}") from e
        except franklinwh.client.GatewayOfflineException as e:
            raise UpdateFailed(f"Gateway offline: {e}") from e
        except franklinwh.client.AccountLockedException as e:
            raise UpdateFailed(f"Account locked: {e}") from e
        except franklinwh.client.InvalidCredentialsException as e:
            raise UpdateFailed(f"Invalid credentials: {e}") from e
        except Exception as e:  # noqa: BLE001
            # get_tou_list() is a newer endpoint; some firmware versions may not
            # support it.  Fall through to the get_composite_info() fallback.
            _LOGGER.debug(
                "get_tou_list() raised %s, falling back to composite info",
                type(e).__name__,
            )

        # Fallback: get_composite_info() returns currentWorkMode (1/2/3) using
        # the same encoding as Mode.workMode and is reliable across firmware.
        # Reserves are not updated here — _last_known_reserves carries the most
        # recently fetched values (or YAML defaults on first boot).
        try:
            composite = await client.get_composite_info()
            work_mode = composite.get("currentWorkMode")
            if work_mode is not None:
                mode_name = _WORK_MODE_TO_API.get(int(work_mode))
                if mode_name is not None:
                    _LOGGER.debug(
                        "currentWorkMode=%s → mode %s (reserves from last good fetch: %s)",
                        work_mode,
                        mode_name,
                        _last_known_reserves,
                    )
                    return {"mode": mode_name, "reserves": dict(_last_known_reserves)}
            raise UpdateFailed(f"Unrecognised currentWorkMode: {work_mode!r}")
        except UpdateFailed:
            raise
        except franklinwh.client.DeviceTimeoutException as e:
            raise UpdateFailed(f"Device timeout: {e}") from e
        except franklinwh.client.GatewayOfflineException as e:
            raise UpdateFailed(f"Gateway offline: {e}") from e
        except Exception as e:  # noqa: BLE001
            raise UpdateFailed(f"Error reading operating mode: {e}") from e

    coordinator = DataUpdateCoordinator[dict](
        hass,
        _LOGGER,
        name="franklinwh_mode",
        update_method=_update_data,
        update_interval=update_interval,
        always_update=False,
    )

    # Initial fetch so the entity is available immediately on startup
    await coordinator.async_refresh()

    async_add_entities([OperatingModeSelect(coordinator, prefix, gateway, client)])


class OperatingModeSelect(
    CoordinatorEntity[DataUpdateCoordinator[dict]],
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
    ) -> None:
        """Initializer."""
        super().__init__(coordinator)
        self._attr_name = f"{prefix} Operating Mode"
        self._client = client
        self._attr_unique_id = gateway + "_operating_mode"
        self._optimistic_option: str | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Clear optimistic state once the coordinator confirms the actual mode."""
        self._optimistic_option = None
        super()._handle_coordinator_update()

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
        if self._optimistic_option is not None:
            return self._optimistic_option
        if self.coordinator.data is None:
            return None
        return _API_TO_OPTION.get(self.coordinator.data["mode"])

    async def async_select_option(self, option: str) -> None:
        """Change the operating mode."""
        if option not in _OPTION_TO_MODE_FACTORY:
            _LOGGER.error("Unknown operating mode option: %s", option)
            return

        if self.coordinator.data is None:
            _LOGGER.error("Cannot switch mode: coordinator data is unavailable")
            return

        work_mode = _OPTION_TO_WORK_MODE[option]
        soc = self.coordinator.data["reserves"].get(work_mode)
        if soc is None:
            _LOGGER.error(
                "No reserve data for %s (workMode=%s) in coordinator data",
                option,
                work_mode,
            )
            return

        mode_obj = _OPTION_TO_MODE_FACTORY[option](soc=int(soc))

        _LOGGER.info(
            "Setting FranklinWH operating mode to: %s (reserve=%s%%)", option, soc
        )

        # Optimistically reflect the new mode in the UI immediately, before the
        # API call completes. _handle_coordinator_update() clears this once the
        # coordinator confirms the actual state from the gateway.
        self._optimistic_option = option
        self.async_write_ha_state()

        try:
            await self._client.set_mode(mode_obj)
        except httpx.ReadTimeout:
            # The API frequently times out even when the command succeeds.
            # The coordinator refresh below will confirm the actual state.
            _LOGGER.warning(
                "set_mode(%s) timed out — command may still have been applied",
                option,
            )

        # Refresh to confirm the actual state and clear the optimistic value.
        await self.coordinator.async_refresh()
