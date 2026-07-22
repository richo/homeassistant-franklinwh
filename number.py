"""Number platform for FranklinWH grid export power limit.

Allows setting the maximum power (kW) exported to the grid. The current
export mode (Solar Only / Solar+aPower / No Export) is preserved when
only the limit is changed.

This platform reuses the coordinator created by the select platform
(which already polls export settings). If the select platform isn't
configured, it creates its own coordinator as a fallback.
"""

from __future__ import annotations

from datetime import timedelta
import logging

import franklinwh
import franklinwh.client
import voluptuous as vol

try:
    import httpx
    _TIMEOUT_ERRORS = (httpx.ReadTimeout, httpx.ConnectTimeout)
except ImportError:
    _TIMEOUT_ERRORS = (TimeoutError,)

from homeassistant.components.number import (
    PLATFORM_SCHEMA as NUMBER_PLATFORM_SCHEMA,
    NumberEntity,
    NumberMode,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME, UnitOfPower
from homeassistant.core import HomeAssistant
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
    get_shared_coordinator,
    handle_rate_limit,
    set_shared_coordinator,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = 60

PLATFORM_SCHEMA = NUMBER_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_ID): cv.string,
        vol.Optional("prefix", default="FranklinWH"): cv.string,
        vol.Optional(
            "update_interval", default=DEFAULT_UPDATE_INTERVAL
        ): cv.time_period,
        vol.Optional("max_export_kw", default=10.0): vol.Coerce(float),
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the number platform."""
    username: str = config[CONF_USERNAME]
    password: str = config[CONF_PASSWORD]
    gateway: str = config[CONF_ID]
    prefix: str = config["prefix"]
    update_interval: timedelta = config["update_interval"]
    max_export_kw: float = config["max_export_kw"]

    client = get_shared_client(hass, username, password, gateway)

    # Reuse the select platform's coordinator if available — it already
    # polls operating mode + export settings, so no need to duplicate.
    coordinator = get_shared_coordinator(hass, gateway, "mode")

    if coordinator is None:
        _LOGGER.debug(
            "Select platform coordinator not found — creating standalone "
            "coordinator for export limit (consider adding the select platform)"
        )

        async def _update_data() -> dict:
            check_rate_limit(hass)
            try:
                settings = await client.get_export_settings()
                clear_rate_limit(hass)
                return {
                    "export_mode": settings.mode.name.lower(),
                    "export_limit_kw": settings.limit_kw,
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
                if "181" in str(err):
                    handle_rate_limit(hass)
                raise UpdateFailed(
                    f"Error fetching FranklinWH export settings: {err}"
                ) from err

        coordinator = DataUpdateCoordinator[dict](
            hass,
            _LOGGER,
            name="franklinwh_export_limit",
            update_method=_update_data,
            update_interval=update_interval,
            always_update=False,
        )
        await coordinator.async_refresh()
        set_shared_coordinator(hass, gateway, "mode", coordinator)
    else:
        _LOGGER.debug("Reusing select platform coordinator for export limit")

    async_add_entities(
        [
            ExportLimitNumber(coordinator, prefix, gateway, client, max_export_kw),
            ReserveSOCNumber(hass, prefix, gateway),
        ]
    )


class ExportLimitNumber(
    CoordinatorEntity[DataUpdateCoordinator[dict]], NumberEntity
):
    """Number entity for the FranklinWH grid export power limit.

    Sets the maximum power (kW) exported to the grid. The export mode
    is preserved when only the limit is changed.
    """

    _attr_native_min_value = 0.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict],
        prefix: str,
        gateway: str,
        client,
        max_export_kw: float,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{prefix} Export Limit"
        self._attr_unique_id = f"{gateway}_export_limit"
        self._attr_native_max_value = max_export_kw
        self._client = client

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        limit = self.coordinator.data.get("export_limit_kw")
        if limit is None:
            return self._attr_native_max_value
        return limit

    async def async_set_native_value(self, value: float) -> None:
        """Set the export power limit, preserving current export mode."""
        limit_kw = None if value >= self._attr_native_max_value else value

        try:
            settings = await self._client.get_export_settings()
            await self._client.set_export_settings(settings.mode, limit_kw)
        except _TIMEOUT_ERRORS:
            _LOGGER.warning(
                "set_export_settings timed out — command may still have been applied"
            )

        await self.coordinator.async_refresh()


class ReserveSOCNumber(RestoreEntity, NumberEntity):
    """Number entity for the FranklinWH power reserve (SOC %).

    This is a LOCAL setting that controls what reserve SOC is sent to the
    API when switching operating modes via the Operating Mode select entity.

    The FranklinWH API requires a 'soc' parameter on every mode switch,
    and it overwrites the stored reserve. The TOU schedule reserve (set
    in the Franklin app) cannot be reliably read via the API. This entity
    gives the user explicit control over what value is sent.

    Set this BEFORE switching modes to ensure the correct reserve is applied.

    Uses RestoreEntity to persist the value across HA restarts.
    """

    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 5.0
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:battery-alert-variant-outline"

    def __init__(self, hass: HomeAssistant, prefix: str, gateway: str) -> None:
        self._hass_ref = hass
        self._attr_name = f"{prefix} Reserve SOC"
        self._attr_unique_id = f"{gateway}_reserve_soc"
        self._value: float = 20.0

    async def async_added_to_hass(self) -> None:
        """Restore previous value on startup.

        Priority:
        1. Restore from HA state (previous session — most reliable)
        2. Read from device via _switch_status() (first install — best guess)
        3. Fall back to 20% (safe default)

        On first install, the device value is the best we can do. The TOU
        schedule reserve may differ from the mode-level SOC fields, so we
        log a warning to prompt the user to verify.
        """
        await super().async_added_to_hass()

        # Priority 1: restore from previous HA session
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            self._value = float(last_state.state)
            _LOGGER.debug("Restored FranklinWH reserve SOC from HA state: %s%%", self._value)
        else:
            # Priority 2: read from device (first install)
            client = self.hass.data.get(DOMAIN, {}).get(
                f"client_{self._attr_unique_id.replace('_reserve_soc', '')}"
            )
            if client:
                try:
                    sw = await client._switch_status()
                    # Read the reserve for the currently active mode
                    for key in ("touMinSoc", "selfMinSoc", "backupMaxSoc"):
                        val = sw.get(key)
                        if val is not None and val != 20:
                            # Found a non-default reserve — likely user-configured
                            self._value = float(val)
                            _LOGGER.info(
                                "Read initial reserve SOC from device: %s%% (%s). "
                                "Verify this matches your Franklin app settings.",
                                val, key,
                            )
                            break
                    else:
                        _LOGGER.warning(
                            "FranklinWH reserve SOC defaulting to 20%%. "
                            "Set this to match your Franklin app Power Reserve "
                            "before switching modes via HA."
                        )
                except Exception:  # noqa: BLE001
                    _LOGGER.debug("Could not read reserve from device, using default 20%%")

        self.hass.data.setdefault(DOMAIN, {})["reserve_soc_override"] = int(self._value)

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Set the reserve SOC that will be used on the next mode switch."""
        self._value = round(value)
        self.hass.data.setdefault(DOMAIN, {})["reserve_soc_override"] = int(self._value)
        _LOGGER.info("FranklinWH reserve SOC set to %s%%", int(self._value))
        self.async_write_ha_state()
