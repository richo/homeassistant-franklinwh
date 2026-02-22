"""Sensor platform for FranklinWH."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

import franklinwh
import httpx
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    MAJOR_VERSION as HASS_MAJOR_VERSION,
    MINOR_VERSION as HASS_MINOR_VERSION,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    __short_version__,
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
DEFAULT_UPDATE_INTERVAL = 30

PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_ID): cv.string,
        vol.Optional("use_sn", default=False): cv.boolean,
        vol.Optional("prefix", default=False): cv.string,
        vol.Optional(
            "update_interval", default=DEFAULT_UPDATE_INTERVAL
        ): cv.time_period,
        vol.Optional("tolerate_stale_data", default=False): cv.boolean,
    }
)


class StaleDataCache:
    """Cache data fetch."""

    def __init__(self) -> None:
        """Empty cache."""
        self.last_data: franklinwh.Stats | None = None

    def store(self, data: franklinwh.Stats) -> None:
        """Cache data fetch."""
        self.last_data = data

    def is_populated(self) -> bool:
        """Is cache populated?"""
        return self.last_data is not None

    def data(self) -> franklinwh.Stats:
        """Retrieve cached data."""
        assert self.last_data is not None, "Cache is not populated"
        return self.last_data


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
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
    if __short_version__ >= "2026.2":
        # pylint: disable=no-name-in-module,import-outside-toplevel
        from homeassistant.helpers.httpx_client import (  # noqa: PLC0415
            SSL_ALPN_HTTP11_HTTP2,  # type: ignore  # noqa: PGH003
            create_async_httpx_client,
        )
        # pylint: enable=no-name-in-module,import-outside-toplevel

        def get_client() -> httpx.AsyncClient:
            return create_async_httpx_client(hass, alpn_protocols=SSL_ALPN_HTTP11_HTTP2)

        franklinwh.HttpClientFactory.set_client_factory(get_client)
        client = franklinwh.Client(fetcher, gateway)
    else:
        client = await hass.async_add_executor_job(franklinwh.Client, fetcher, gateway)

    cache = StaleDataCache()

    async def _update_data() -> franklinwh.Stats:
        max_retries = 3
        retry_delay = 2  # seconds

        _LOGGER.debug("Fetching latest data from FranklinWH")
        for attempt in range(max_retries):
            if attempt > 0:
                _LOGGER.warning("Trying again")
                await asyncio.sleep(retry_delay)
            try:
                data = await client.get_stats()
            except franklinwh.client.DeviceTimeoutException as e:
                _LOGGER.warning(
                    "Error getting data from FranklinWH - Device Timeout: %s", e
                )
            except franklinwh.client.GatewayOfflineException as e:
                _LOGGER.warning(
                    "Error getting data from FranklinWH - Gateway Offline %s", e
                )
            except franklinwh.client.AccountLockedException as e:
                _LOGGER.warning(
                    "Error getting data from FranklinWH - Account Locked %s", e
                )
            except franklinwh.client.InvalidCredentialsException as e:
                _LOGGER.warning(
                    "Error getting data from FranklinWH - Invalid Credentials %s", e
                )
            else:
                if attempt > 0:
                    _LOGGER.warning(
                        "Successfully fetched data from FranklinWH after retry"
                    )
                else:
                    _LOGGER.debug("Fetched latest data from FranklinWH: %s", data)
                cache.store(data)
                return data

        _LOGGER.warning(
            "Failed to fetch data from FranklinWH after %s attempts", max_retries
        )

        if config["tolerate_stale_data"] and cache.is_populated():
            return cache.data()

        raise UpdateFailed(
            f"Failed to fetch data from FranklinWH after {max_retries} attempts."
        )

    coordinator = DataUpdateCoordinator[franklinwh.Stats](
        hass,
        _LOGGER,
        name="franklinwh",
        update_method=_update_data,
        update_interval=update_interval,
        always_update=False,
    )

    # Initial fetch (If we don't kick this off manually, we'll get unavailable
    # sensors until the first scheduled update).
    await coordinator.async_refresh()

    async_add_entities(
        [
            FranklinBatterySensor(coordinator, prefix, unique_id),
            HomeLoadSensor(coordinator, prefix, unique_id),
            HomeUseSensor(coordinator, prefix, unique_id),
            BatteryUseSensor(coordinator, prefix, unique_id),
            GridUseSensor(coordinator, prefix, unique_id),
            GridStatusSensor(coordinator, prefix, unique_id),
            SolarProductionSensor(coordinator, prefix, unique_id),
            BatteryChargeSensor(coordinator, prefix, unique_id),
            BatteryDischargeSensor(coordinator, prefix, unique_id),
            GeneratorUseSensor(coordinator, prefix, unique_id),
            GridImportSensor(coordinator, prefix, unique_id),
            GridExportSensor(coordinator, prefix, unique_id),
            SolarEnergySensor(coordinator, prefix, unique_id),
            Sw1LoadSensor(coordinator, prefix, unique_id),
            Sw1UseSensor(coordinator, prefix, unique_id),
            Sw2LoadSensor(coordinator, prefix, unique_id),
            Sw2UseSensor(coordinator, prefix, unique_id),
            V2LUseSensor(coordinator, prefix, unique_id),
            V2LExportSensor(coordinator, prefix, unique_id),
            V2LImportSensor(coordinator, prefix, unique_id),
        ]
    )


class FranklinSensor(
    CoordinatorEntity[DataUpdateCoordinator[franklinwh.Stats]], SensorEntity
):
    """Base class for FranklinWH sensors."""

    def __init__(self, coordinator, prefix, unique_id, unique_id_suffix) -> None:
        """Initializer."""
        super().__init__(coordinator)
        self._attr_name = prefix + " " + unique_id_suffix.replace("_", " ").title()
        if unique_id_suffix and unique_id:
            self._attr_has_entity_name = True
            self._attr_unique_id = unique_id + unique_id_suffix

    @property
    def available(self) -> bool:
        """Is the sensor available?"""
        return (
            self.coordinator.last_update_success and self.coordinator.data is not None
        )


class FranklinBatterySensor(FranklinSensor):
    """Shows the current state of charge of the battery."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_state_of_charge")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.battery_soc


class HomeLoadSensor(FranklinSensor):
    """Shows the current power use by the home load."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_home_load")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.home_load


class HomeUseSensor(FranklinSensor):
    """Shows the total energy used by the home."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_home_use")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.home_use


class GridUseSensor(FranklinSensor):
    """Shows the current import or export from the grid."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_grid_use")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.grid_use


class GridStatusSensor(FranklinSensor):
    """Shows the current status of the grid."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [status.name for status in franklinwh.GridStatus]

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_grid_status")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.grid_status.name


class GridImportSensor(FranklinSensor):
    """Shows the amount of energy imported from the grid."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_grid_import")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.grid_import


class GridExportSensor(FranklinSensor):
    """Shows the amount of energy exported to the grid."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_grid_export")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.grid_export


class SolarProductionSensor(FranklinSensor):
    """Shows the current solar production."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_solar_production")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.solar_production


class SolarEnergySensor(FranklinSensor):
    """Shows the energy generated by solar."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_solar_energy")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.solar


class BatteryUseSensor(FranklinSensor):
    """Shows the current charge or discharge from the battery."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_battery_use")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.battery_use


class BatteryChargeSensor(FranklinSensor):
    """Shows the charging stats of the battery."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_battery_charge")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.battery_charge


class BatteryDischargeSensor(FranklinSensor):
    """Shows the charging stats of the battery."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_battery_discharge")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.battery_discharge


class GeneratorUseSensor(FranklinSensor):
    """Shows the current power output of the generator."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_generator_use")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.generator_production


class GeneratorEnergySensor(FranklinSensor):
    """Shows the energy imported from the generator."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_generator_energy")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.generator


class Sw1LoadSensor(FranklinSensor):
    """Shows the current power use by switch 1."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_switch_1_load")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.switch_1_load


class Sw1UseSensor(FranklinSensor):
    """Shows the lifetime energy usage by switch 1."""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_switch_1_lifetime_use")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.switch_1_use


class Sw2LoadSensor(FranklinSensor):
    """Shows the current power use by switch 2."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_switch_2_load")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.switch_2_load


class Sw2UseSensor(FranklinSensor):
    """Shows the lifetime energy usage by switch 1."""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_switch_2_lifetime_use")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.switch_2_use


class V2LUseSensor(FranklinSensor):
    """Shows the current power use by the car switch."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_v2l_use")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.current.v2l_use


class V2LExportSensor(FranklinSensor):
    """Shows the lifetime energy exported to the car switch."""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_v2l_export")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.v2l_export


class V2LImportSensor(FranklinSensor):
    """Shows the lifetime energy exported to the car switch."""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id) -> None:
        """Initializer."""
        super().__init__(coordinator, prefix, unique_id, "_v2l_import")

    @property
    def native_value(self):
        """Value."""
        return self.coordinator.data.totals.v2l_import
