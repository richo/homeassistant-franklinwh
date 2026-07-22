"""Select platform for FranklinWH operating mode and grid export control.

Exposes two select entities:
- Operating Mode (Time of Use / Self Consumption / Emergency Backup)
- Export Mode (Solar Only / Solar and aPower / No Export)

Mode detection uses get_composite_info().currentWorkMode as the primary
source (reliable across firmware versions), with get_mode() as fallback.

Reserve SOC is read from the device and preserved when changing modes —
the integration never overwrites reserves configured in the Franklin app.
"""

from __future__ import annotations

from datetime import timedelta
import logging

import franklinwh
import franklinwh.client
try:
    import httpx
    _TIMEOUT_ERRORS = (httpx.ReadTimeout, httpx.ConnectTimeout)
except ImportError:
    _TIMEOUT_ERRORS = (TimeoutError,)
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

from . import (
    DOMAIN,
    check_rate_limit,
    clear_rate_limit,
    get_shared_client,
    handle_rate_limit,
    set_shared_coordinator,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = 60

# ── Operating mode mappings ──────────────────────────────────────────

# Human-readable labels for the HA UI
OPTION_TIME_OF_USE = "Time of Use"
OPTION_SELF_CONSUMPTION = "Self Consumption"
OPTION_EMERGENCY_BACKUP = "Emergency Backup"

OPERATING_MODE_OPTIONS = [
    OPTION_TIME_OF_USE,
    OPTION_SELF_CONSUMPTION,
    OPTION_EMERGENCY_BACKUP,
]

# Map from franklinwh library mode strings → UI labels
_API_MODE_TO_OPTION: dict[str, str] = {
    "time_of_use": OPTION_TIME_OF_USE,
    "self_consumption": OPTION_SELF_CONSUMPTION,
    "emergency_backup": OPTION_EMERGENCY_BACKUP,
}

# Map from UI labels → Mode factory callables
_OPTION_TO_MODE_FACTORY = {
    OPTION_TIME_OF_USE: franklinwh.Mode.time_of_use,
    OPTION_SELF_CONSUMPTION: franklinwh.Mode.self_consumption,
    OPTION_EMERGENCY_BACKUP: franklinwh.Mode.emergency_backup,
}

# Map from get_composite_info().currentWorkMode (1/2/3) → API mode string.
# This is the most reliable source across firmware versions.
_WORK_MODE_TO_API: dict[int, str] = {
    1: "time_of_use",
    2: "self_consumption",
    3: "emergency_backup",
}

# Map from _switch_status().runingMode → API mode string (fallback only).
_RUNNING_MODE_TO_API: dict[int, str] = {
    7167: "self_consumption",
    7168: "emergency_backup",
    7169: "time_of_use",
}

# SOC key names in _switch_status() per mode
_SOC_KEYS: dict[str, str] = {
    "self_consumption": "selfMinSoc",
    "time_of_use": "touMinSoc",
    "emergency_backup": "backupMaxSoc",
}

# ── Export mode mappings ─────────────────────────────────────────────

OPTION_SOLAR_ONLY = "Solar Only"
OPTION_SOLAR_AND_APOWER = "Solar and aPower"
OPTION_NO_EXPORT = "No Export"

EXPORT_MODE_OPTIONS = [OPTION_SOLAR_ONLY, OPTION_SOLAR_AND_APOWER, OPTION_NO_EXPORT]

_EXPORT_OPTION_TO_ENUM: dict[str, franklinwh.ExportMode] = {
    OPTION_SOLAR_ONLY: franklinwh.ExportMode.SOLAR_ONLY,
    OPTION_SOLAR_AND_APOWER: franklinwh.ExportMode.SOLAR_AND_APOWER,
    OPTION_NO_EXPORT: franklinwh.ExportMode.NO_EXPORT,
}

_EXPORT_ENUM_TO_OPTION: dict[str, str] = {
    "solar_only": OPTION_SOLAR_ONLY,
    "solar_and_apower": OPTION_SOLAR_AND_APOWER,
    "no_export": OPTION_NO_EXPORT,
}

# ── Platform schema ─────────────────────────────────────────────────

PLATFORM_SCHEMA = SELECT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_ID): cv.string,
        vol.Optional("prefix", default="FranklinWH"): cv.string,
        vol.Optional(
            "update_interval", default=DEFAULT_UPDATE_INTERVAL
        ): cv.time_period,
    }
)


# ── Mode detection helpers ───────────────────────────────────────────


async def _read_operating_mode(client: franklinwh.Client) -> tuple[str | None, int | None]:
    """Read the current operating mode and reserve SOC from the device.

    Tries get_composite_info().currentWorkMode first (most reliable across
    firmware versions), then get_mode(), then _switch_status().runingMode.

    Returns (api_mode_string, reserve_soc).
    """
    api_mode: str | None = None

    # Primary: currentWorkMode from composite info
    try:
        composite = await client.get_composite_info()
        work_mode = composite.get("currentWorkMode")
        if work_mode is not None:
            api_mode = _WORK_MODE_TO_API.get(int(work_mode))
            if api_mode:
                _LOGGER.debug("Mode from currentWorkMode=%s → %s", work_mode, api_mode)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("get_composite_info failed (%s), trying get_mode", err)

    # Fallback 1: library get_mode()
    if api_mode is None:
        try:
            mode_name, _ = await client.get_mode()
            if mode_name in _API_MODE_TO_OPTION:
                api_mode = mode_name
                _LOGGER.debug("Mode from get_mode() → %s", api_mode)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("get_mode failed (%s), trying _switch_status", err)

    # Fallback 2: runingMode from _switch_status
    # Note: we call the private _switch_status() because the library's own
    # get_mode() uses it internally and the maintainer has a TODO noting the
    # MODE_MAP values may be wrong on some firmware.
    sw: dict | None = None
    if api_mode is None:
        try:
            sw = await client._switch_status()
            running_mode = sw.get("runingMode")
            api_mode = _RUNNING_MODE_TO_API.get(running_mode)
            if api_mode:
                _LOGGER.debug("Mode from runingMode=%s → %s", running_mode, api_mode)
            else:
                _LOGGER.warning("Unrecognised runingMode: %r", running_mode)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("All mode detection methods failed: %s", err)

    # Read reserve SOC for the detected mode (reuse cached _switch_status)
    reserve_soc: int | None = None
    if api_mode:
        soc_key = _SOC_KEYS.get(api_mode)
        if soc_key:
            try:
                if sw is None:
                    sw = await client._switch_status()
                reserve_soc = sw.get(soc_key)
            except Exception:  # noqa: BLE001
                pass

    return api_mode, reserve_soc


async def _read_export_settings(client: franklinwh.Client) -> tuple[str | None, float | None]:
    """Read grid export mode and limit. Returns (export_mode, limit_kw)."""
    settings = await client.get_export_settings()
    mode = settings.mode.name.lower()
    return mode, settings.limit_kw


# ── Platform setup ───────────────────────────────────────────────────


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
    prefix: str = config["prefix"]
    update_interval: timedelta = config["update_interval"]

    client = get_shared_client(hass, username, password, gateway)

    async def _update_data() -> dict:
        # Circuit breaker: skip API call if we're in a backoff period
        check_rate_limit(hass)
        try:
            operating_mode, reserve_soc = await _read_operating_mode(client)
            export_mode, export_limit_kw = await _read_export_settings(client)
            clear_rate_limit(hass)  # Successful — reset backoff
            return {
                "operating_mode": operating_mode,
                "reserve_soc": reserve_soc,
                "export_mode": export_mode,
                "export_limit_kw": export_limit_kw,
            }
        except franklinwh.client.AccountLockedException as err:
            handle_rate_limit(hass)
            raise UpdateFailed(f"Account locked / rate limited: {err}") from err
        except franklinwh.client.DeviceTimeoutException as err:
            raise UpdateFailed(f"Device timeout: {err}") from err
        except franklinwh.client.GatewayOfflineException as err:
            raise UpdateFailed(f"Gateway offline: {err}") from err
        except franklinwh.client.InvalidCredentialsException as err:
            raise UpdateFailed(f"Invalid credentials: {err}") from err
        except Exception as err:
            # Check for code 181 in the error message
            if "181" in str(err):
                handle_rate_limit(hass)
            raise UpdateFailed(
                f"Error fetching FranklinWH mode/export status: {err}"
            ) from err

    coordinator = DataUpdateCoordinator[dict](
        hass,
        _LOGGER,
        name="franklinwh_mode",
        update_method=_update_data,
        update_interval=update_interval,
        always_update=False,
    )

    await coordinator.async_refresh()

    # Store coordinator so the number platform can reuse it instead of
    # making duplicate API calls for export settings.
    set_shared_coordinator(hass, gateway, "mode", coordinator)

    async_add_entities(
        [
            OperatingModeSelect(coordinator, prefix, gateway, client),
            ExportModeSelect(coordinator, prefix, gateway, client),
        ]
    )


# ── Base class ───────────────────────────────────────────────────────


class FranklinSelectBase(
    CoordinatorEntity[DataUpdateCoordinator[dict]], SelectEntity
):
    """Base class for FranklinWH select entities."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict],
        prefix: str,
        gateway: str,
        client: franklinwh.Client,
        name_suffix: str,
        unique_id_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{prefix} {name_suffix}"
        self._attr_unique_id = f"{gateway}{unique_id_suffix}"
        self._client = client
        self._optimistic_option: str | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Clear optimistic state when the coordinator confirms actual state."""
        self._optimistic_option = None
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )


# ── Operating mode select ────────────────────────────────────────────


class OperatingModeSelect(FranklinSelectBase):
    """Select entity for the FranklinWH operating mode.

    Reads the current reserve SOC from the device and preserves it when
    changing modes — never overwrites reserves set in the Franklin app.
    """

    _attr_options = OPERATING_MODE_OPTIONS

    def __init__(self, coordinator, prefix, gateway, client) -> None:
        super().__init__(
            coordinator, prefix, gateway, client,
            "Operating Mode", "_operating_mode",
        )

    @property
    def current_option(self) -> str | None:
        if self._optimistic_option is not None:
            return self._optimistic_option
        if self.coordinator.data:
            api_mode = self.coordinator.data.get("operating_mode")
            return _API_MODE_TO_OPTION.get(api_mode) if api_mode else None
        return None

    async def async_select_option(self, option: str) -> None:
        """Change operating mode.

        WARNING: The FranklinWH API requires a 'soc' (reserve) parameter
        when switching modes, and it OVERWRITES the existing reserve.
        The TOU schedule reserve (e.g. 35%) is stored separately from the
        mode-level reserve (touMinSoc/selfMinSoc/backupMaxSoc) and we
        cannot reliably read it. We use the mode-level value from
        _switch_status() as the best available approximation.

        Users should verify their Power Reserve in the Franklin app after
        switching modes via HA.
        """
        if option not in _OPTION_TO_MODE_FACTORY:
            _LOGGER.error("Unknown operating mode: %s", option)
            return

        # Use the reserve from the Reserve SOC number entity if available
        # (user-controlled, accurate). Fall back to _switch_status() value.
        reserve_override = self.hass.data.get(DOMAIN, {}).get("reserve_soc_override")
        if reserve_override is not None:
            reserve_soc = int(reserve_override)
            _LOGGER.debug("Using reserve SOC override: %s%%", reserve_soc)
        else:
            reserve_soc = (
                self.coordinator.data.get("reserve_soc")
                if self.coordinator.data
                else None
            )

        kwargs = {"soc": int(reserve_soc)} if reserve_soc is not None else {}
        mode_obj = _OPTION_TO_MODE_FACTORY[option](**kwargs)

        _LOGGER.info(
            "Setting FranklinWH mode to %s (reserve=%s%%)",
            option, reserve_soc,
        )

        self._optimistic_option = option
        self.async_write_ha_state()

        try:
            await self._client.set_mode(mode_obj)
        except _TIMEOUT_ERRORS:
            _LOGGER.warning(
                "set_mode(%s) timed out — command may still have been applied",
                option,
            )

        await self.coordinator.async_refresh()


# ── Export mode select ───────────────────────────────────────────────


class ExportModeSelect(FranklinSelectBase):
    """Select entity for grid export mode.

    Preserves the current export power limit when changing modes.
    """

    _attr_options = EXPORT_MODE_OPTIONS

    def __init__(self, coordinator, prefix, gateway, client) -> None:
        super().__init__(
            coordinator, prefix, gateway, client,
            "Export Mode", "_export_mode",
        )

    @property
    def current_option(self) -> str | None:
        if self._optimistic_option is not None:
            return self._optimistic_option
        if self.coordinator.data:
            api_mode = self.coordinator.data.get("export_mode")
            return _EXPORT_ENUM_TO_OPTION.get(api_mode) if api_mode else None
        return None

    async def async_select_option(self, option: str) -> None:
        """Change export mode, preserving the current power limit."""
        if option not in _EXPORT_OPTION_TO_ENUM:
            _LOGGER.error("Unknown export mode: %s", option)
            return

        limit_kw = (
            self.coordinator.data.get("export_limit_kw")
            if self.coordinator.data
            else None
        )

        _LOGGER.info("Setting FranklinWH export mode to %s", option)

        self._optimistic_option = option
        self.async_write_ha_state()

        try:
            await self._client.set_export_settings(
                _EXPORT_OPTION_TO_ENUM[option], limit_kw
            )
        except _TIMEOUT_ERRORS:
            _LOGGER.warning(
                "set_export_settings(%s) timed out — command may still have been applied",
                option,
            )

        await self.coordinator.async_refresh()
