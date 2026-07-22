"""Select platform for FranklinWH operating mode and grid export control."""

from __future__ import annotations

from datetime import timedelta
import logging

import franklinwh
import voluptuous as vol

from homeassistant.components.select import (
    PLATFORM_SCHEMA as SELECT_PLATFORM_SCHEMA,
    SelectEntity,
)
from homeassistant.const import (
    CONF_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
)
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

# Poll mode/export status every 5 minutes — they rarely change
DEFAULT_UPDATE_INTERVAL = 300

_EXPORT_MODE_MAP = {
    "solar_only": franklinwh.ExportMode.SOLAR_ONLY,
    "solar_and_apower": franklinwh.ExportMode.SOLAR_AND_APOWER,
    "no_export": franklinwh.ExportMode.NO_EXPORT,
}

# Correct runingMode values for current firmware (the library's built-in
# MODE_MAP uses different keys and may not match all firmware versions)
_RUNNING_MODE_MAP = {
    7167: "self_consumption",
    7168: "emergency_backup",
    7169: "time_of_use",
}

OPERATING_MODES = ["self_consumption", "time_of_use", "emergency_backup"]
EXPORT_MODES = ["solar_only", "solar_and_apower", "no_export"]

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
    }
)


async def _read_operating_mode(client) -> tuple[str | None, int | None]:
    """Read the current operating mode and reserve SOC from the device.

    Tries the high-level _status() endpoint (command 203) first, reading
    the human-readable 'name' field which is firmware-version independent.
    Falls back to _switch_status() (command 311) with numeric runingMode
    lookup if the name field is absent or unrecognised.

    Returns (mode_name, reserve_soc).
    """
    soc_key_map = {
        "self_consumption": "selfMinSoc",
        "time_of_use": "touMinSoc",
        "emergency_backup": "backupMaxSoc",
    }

    # Primary: human-readable name from high-level status
    try:
        status = await client._status()
        name = (status.get("name") or "").lower()
        if "self" in name and "consumption" in name:
            mode = "self_consumption"
        elif "emergency" in name or "backup" in name:
            mode = "emergency_backup"
        elif "tou" in name or "time" in name:
            mode = "time_of_use"
        else:
            mode = None

        if mode:
            sw = await client._switch_status()
            reserve = sw.get(soc_key_map[mode])
            return mode, reserve
        if name:
            _LOGGER.debug(
                "get_mode: _status name %r unrecognised — trying _switch_status",
                status.get("name"),
            )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("get_mode: _status failed (%s) — trying _switch_status", err)

    # Fallback: numeric runingMode
    sw = await client._switch_status()
    running_mode = sw.get("runingMode")
    mode = _RUNNING_MODE_MAP.get(running_mode)
    if mode is None:
        _LOGGER.warning("get_mode: unrecognised runingMode %r", running_mode)
    reserve = sw.get(soc_key_map[mode]) if mode else None
    return mode, reserve


async def _read_export_settings(client) -> tuple[str, float | None]:
    """Read the current grid export mode and limit from the API.

    Returns (export_mode, limit_kw) where limit_kw is None for unlimited.
    """
    settings = await client.get_export_settings()
    mode = settings.mode.name.lower()
    return mode, settings.limit_kw


async def _write_export_settings(
    client, mode: str, limit_kw: float | None
) -> None:
    """Write the grid export mode and optional power limit to the API."""
    await client.set_export_settings(_EXPORT_MODE_MAP[mode], limit_kw)


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

    async def _update_data() -> dict:
        try:
            operating_mode, reserve_soc = await _read_operating_mode(client)
            export_mode, export_limit_kw = await _read_export_settings(client)
            return {
                "operating_mode": operating_mode,
                "reserve_soc": reserve_soc,
                "export_mode": export_mode,
                "export_limit_kw": export_limit_kw,
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching FranklinWH mode/export status: {err}") from err

    coordinator = DataUpdateCoordinator[dict](
        hass,
        _LOGGER,
        name="franklinwh_mode",
        update_method=_update_data,
        update_interval=update_interval,
        always_update=False,
    )

    await coordinator.async_refresh()

    async_add_entities(
        [
            OperatingModeSelect(coordinator, prefix, unique_id, client),
            ExportModeSelect(coordinator, prefix, unique_id, client),
        ]
    )


class FranklinSelectBase(
    CoordinatorEntity[DataUpdateCoordinator[dict]], SelectEntity
):
    """Base class for FranklinWH select entities."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict],
        prefix: str,
        unique_id: str | None,
        client,
        name_suffix: str,
        unique_id_suffix: str,
    ) -> None:
        """Initializer."""
        super().__init__(coordinator)
        self._attr_name = f"{prefix} {name_suffix}"
        self._client = client
        if unique_id:
            self._attr_has_entity_name = True
            self._attr_unique_id = unique_id + unique_id_suffix

    @property
    def available(self) -> bool:
        """Entity is available when the coordinator has data."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )


class OperatingModeSelect(FranklinSelectBase):
    """Select entity for the FranklinWH operating mode.

    Allows switching between Self Consumption, Time of Use, and Emergency
    Backup directly from Home Assistant. The current reserve SOC is read
    from the device and preserved when changing modes.
    """

    _attr_options = OPERATING_MODES

    def __init__(self, coordinator, prefix, unique_id, client) -> None:
        """Initializer."""
        super().__init__(
            coordinator,
            prefix,
            unique_id,
            client,
            "Operating Mode",
            "_operating_mode",
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently active operating mode."""
        if self.coordinator.data:
            return self.coordinator.data.get("operating_mode")
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the operating mode, preserving the current reserve SOC."""
        reserve_soc = (
            self.coordinator.data.get("reserve_soc")
            if self.coordinator.data
            else None
        )

        if option == "emergency_backup":
            soc = int(reserve_soc) if reserve_soc is not None else 100
            mode = franklinwh.Mode.emergency_backup(soc=soc)
        elif option == "self_consumption":
            kwargs = {"soc": int(reserve_soc)} if reserve_soc is not None else {}
            mode = franklinwh.Mode.self_consumption(**kwargs)
        elif option == "time_of_use":
            kwargs = {"soc": int(reserve_soc)} if reserve_soc is not None else {}
            mode = franklinwh.Mode.time_of_use(**kwargs)
        else:
            _LOGGER.error("Unknown operating mode: %s", option)
            return

        await self._client.set_mode(mode)
        # Optimistically update local state — the device takes a moment to
        # apply the change so an immediate API read-back may not reflect it yet.
        if self.coordinator.data is not None:
            self.coordinator.data["operating_mode"] = option
        self.async_write_ha_state()


class ExportModeSelect(FranklinSelectBase):
    """Select entity for the FranklinWH grid export mode.

    Controls whether solar only, solar and battery, or no power is exported
    to the grid. The current export power limit is preserved when changing
    modes.
    """

    _attr_options = EXPORT_MODES

    def __init__(self, coordinator, prefix, unique_id, client) -> None:
        """Initializer."""
        super().__init__(
            coordinator,
            prefix,
            unique_id,
            client,
            "Export Mode",
            "_export_mode",
        )

    @property
    def current_option(self) -> str | None:
        """Return the current grid export mode."""
        if self.coordinator.data:
            return self.coordinator.data.get("export_mode")
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the export mode, preserving the current power limit."""
        if option not in _EXPORT_MODE_MAP:
            _LOGGER.error("Unknown export mode: %s", option)
            return

        limit_kw = (
            self.coordinator.data.get("export_limit_kw")
            if self.coordinator.data
            else None
        )
        await _write_export_settings(self._client, option, limit_kw)
        # Optimistically update local state
        if self.coordinator.data is not None:
            self.coordinator.data["export_mode"] = option
        self.async_write_ha_state()
