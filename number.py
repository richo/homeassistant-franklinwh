"""Number platform for FranklinWH grid export power limit."""

from __future__ import annotations

from datetime import timedelta
import logging

import franklinwh
import voluptuous as vol

from homeassistant.components.number import (
    PLATFORM_SCHEMA as NUMBER_PLATFORM_SCHEMA,
    NumberEntity,
    NumberMode,
)
from homeassistant.const import (
    CONF_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    UnitOfPower,
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

DEFAULT_UPDATE_INTERVAL = 300


PLATFORM_SCHEMA = NUMBER_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_ID): cv.string,
        vol.Optional("use_sn", default=False): cv.boolean,
        vol.Optional("prefix", default=False): cv.string,
        vol.Optional(
            "update_interval", default=DEFAULT_UPDATE_INTERVAL
        ): cv.time_period,
        vol.Optional("max_export_kw", default=10.0): vol.Coerce(float),
    }
)


async def _read_export_settings(client) -> tuple[str, float | None]:
    """Read the current grid export mode and limit from the API.

    Returns (export_mode, limit_kw) where limit_kw is None for unlimited.
    """
    settings = await client.get_export_settings()
    mode = settings.mode.name.lower()
    return mode, settings.limit_kw


async def _write_export_limit(client, limit_kw: float | None) -> None:
    """Write the grid export power limit, preserving the current export mode."""
    settings = await client.get_export_settings()
    await client.set_export_settings(settings.mode, limit_kw)


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
    update_interval: timedelta = config["update_interval"]
    max_export_kw: float = config["max_export_kw"]

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
            export_mode, export_limit_kw = await _read_export_settings(client)
            return {
                "export_mode": export_mode,
                "export_limit_kw": export_limit_kw,
            }
        except Exception as err:
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

    async_add_entities(
        [ExportLimitNumber(coordinator, prefix, unique_id, client, max_export_kw)]
    )


class ExportLimitNumber(
    CoordinatorEntity[DataUpdateCoordinator[dict]], NumberEntity
):
    """Number entity for the FranklinWH grid export power limit.

    Sets the maximum power (kW) that can be exported to the grid. A value
    of 0 (or the entity being set to the max) with no active limit is
    represented as None internally (unlimited). The export mode
    (solar_only / solar_and_apower / no_export) is preserved when only
    the limit is changed.
    """

    _attr_native_min_value = 0.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict],
        prefix: str,
        unique_id: str | None,
        client,
        max_export_kw: float,
    ) -> None:
        """Initializer."""
        super().__init__(coordinator)
        self._attr_name = f"{prefix} Export Limit"
        self._attr_native_max_value = max_export_kw
        self._client = client
        if unique_id:
            self._attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_export_limit"

    @property
    def available(self) -> bool:
        """Entity is available when the coordinator has data."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )

    @property
    def native_value(self) -> float | None:
        """Return the current export limit in kW.

        Returns None (unknown) when the coordinator has no data, and
        native_max_value when the device reports unlimited (-1 / None)
        so the slider sits at the top of its range.
        """
        if not self.coordinator.data:
            return None
        limit = self.coordinator.data.get("export_limit_kw")
        if limit is None:
            # Unlimited — represent as the maximum slider value
            return self._attr_native_max_value
        return limit

    async def async_set_native_value(self, value: float) -> None:
        """Set the export power limit.

        A value at or above native_max_value is treated as unlimited
        (passes None to the API, which stores -1 / no cap).
        """
        if value >= self._attr_native_max_value:
            limit_kw = None  # unlimited
        else:
            limit_kw = value

        await _write_export_limit(self._client, limit_kw)
        await self.coordinator.async_refresh()
