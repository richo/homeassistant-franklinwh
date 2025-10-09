from __future__ import annotations
from datetime import timedelta
import logging

import franklinwh

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
        UnitOfPower,
        UnitOfEnergy,
        PERCENTAGE,
        CONF_USERNAME,
        CONF_PASSWORD,
        CONF_ID,
        )

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(seconds=10)

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Required(CONF_ID): cv.string,
            vol.Optional("use_sn", default=False): cv.boolean,
            vol.Optional("prefix", default=False): cv.string,
            }
        )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    username: str = config[CONF_USERNAME]
    password: str = config[CONF_PASSWORD]
    gateway: str = config[CONF_ID]

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
    client = await hass.async_add_executor_job(franklinwh.Client, fetcher, gateway)

    async def _update_data():
        _LOGGER.debug("Fetching latest data from FranklinWH")
        data = await hass.async_add_executor_job(client.get_stats)
        _LOGGER.debug("Successfully fetched data")
        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="franklinwh",
        update_method=_update_data,
    )

    async def _refresh_data(_):
        """Refresh data from the coordinator."""
        _LOGGER.debug("Requesting FranklinWH coordinator refresh")
        await coordinator.async_refresh()

    # We do things this way (instead of just providing the update interval
    # to the coordinator) so that we can poll reliably every UPDATE_INTERVAL
    # instead of having UPDATE_INTERVAL _between_ polls (so this method
    # disregards the time taken to do the poll itself).
    async_track_time_interval(hass, _refresh_data, UPDATE_INTERVAL)

    await coordinator.async_refresh()

    async_add_entities([
        FranklinBatterySensor(coordinator, prefix, unique_id),
        HomeLoadSensor(coordinator, prefix, unique_id),
        BatteryUseSensor(coordinator, prefix, unique_id),
        GridUseSensor(coordinator, prefix, unique_id),
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
        ])

class FranklinSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, prefix, unique_id, unique_id_suffix):
        super().__init__(coordinator)
        self._attr_name = prefix + " " + unique_id_suffix.replace("_", " ").title()
        if unique_id_suffix and unique_id:
            self._attr_has_entity_name = True
            self._attr_unique_id = unique_id + unique_id_suffix

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

class FranklinBatterySensor(FranklinSensor):
    """Shows the current state of charge of the battery"""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_state_of_charge")

    @property
    def native_value(self):
        return self.coordinator.data.current.battery_soc

class HomeLoadSensor(FranklinSensor):
    """Shows the current power use by the home load"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_home_load")

    @property
    def native_value(self):
        return self.coordinator.data.current.home_load

class HomeUseSensor(FranklinSensor):
    """Shows the total energy used by the home"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_home_use")

    @property
    def native_value(self):
        return self.coordinator.data.totals.home_use

class GridUseSensor(FranklinSensor):
    """Shows the current import or export from the grid"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_grid_use")

    @property
    def native_value(self):
        return self.coordinator.data.current.grid_use * -1

class GridImportSensor(FranklinSensor):
    """Shows the amount of energy imported from the grid"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_grid_import")

    @property
    def native_value(self):
        return self.coordinator.data.totals.grid_import

class GridExportSensor(FranklinSensor):
    """Shows the amount of energy exported to the grid"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_grid_export")

    @property
    def native_value(self):
        return self.coordinator.data.totals.grid_export

class SolarProductionSensor(FranklinSensor):
    """Shows the current solar production"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_solar_production")

    @property
    def native_value(self):
        return self.coordinator.data.current.solar_production

class SolarEnergySensor(FranklinSensor):
    """Shows the energy generated by solar"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_solar_energy")

    @property
    def native_value(self):
        return self.coordinator.data.totals.solar

class BatteryUseSensor(FranklinSensor):
    """Shows the current charge or discharge from the battery"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_battery_use")

    @property
    def native_value(self):
        return self.coordinator.data.current.battery_use * -1


class BatteryChargeSensor(FranklinSensor):
    """Shows the charging stats of the battery"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_battery_charge")

    @property
    def native_value(self):
        return self.coordinator.data.totals.battery_charge

class BatteryDischargeSensor(FranklinSensor):
    """Shows the charging stats of the battery"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_battery_discharge")

    @property
    def native_value(self):
        return self.coordinator.data.totals.battery_discharge

class GeneratorUseSensor(FranklinSensor):
    """Shows the current power output of the generator"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_generator_use")

    @property
    def native_value(self):
        return self.coordinator.data.current.generator_production

class GeneratorEnergySensor(FranklinSensor):
    """Shows the energy imported from the generator"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_generator_energy")

    @property
    def native_value(self):
        return self.coordinator.data.totals.generator

class Sw1LoadSensor(FranklinSensor):
    """Shows the current power use by switch 1"""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_switch_1_load")

    @property
    def native_value(self):
        return self.coordinator.data.current.switch_1_load

class Sw1UseSensor(FranklinSensor):
    """Shows the lifetime energy usage by switch 1"""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_switch_1_lifetime_use")

    @property
    def native_value(self):
        return self.coordinator.data.totals.switch_1_use


class Sw2LoadSensor(FranklinSensor):
    """Shows the current power use by switch 2"""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_switch_2_load")

    @property
    def native_value(self):
        return self.coordinator.data.current.switch_2_load

class Sw2UseSensor(FranklinSensor):
    """Shows the lifetime energy usage by switch 1"""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_switch_2_lifetime_use")

    @property
    def native_value(self):
        return self.coordinator.data.totals.switch_2_use


class V2LUseSensor(FranklinSensor):
    """Shows the current power use by the car switch"""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_v2l_use")

    @property
    def native_value(self):
        return self.coordinator.data.current.v2l_use

class V2LExportSensor(FranklinSensor):
    """Shows the lifetime energy exported to the car switch"""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_v2l_export")

    @property
    def native_value(self):
        return self.coordinator.data.totals.v2l_export

class V2LImportSensor(FranklinSensor):
    """Shows the lifetime energy exported to the car switch"""



    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, prefix, unique_id):
        super().__init__(coordinator, prefix, unique_id, "_v2l_import")

    @property
    def native_value(self):
        return self.coordinator.data.totals.v2l_import
