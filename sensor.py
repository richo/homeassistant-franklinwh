"""Platform for sensor integration."""
from __future__ import annotations
from threading import Lock
import time

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
PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Required(CONF_ID): cv.string,
            vol.Optional("use_sn"): cv.boolean,
            vol.Optional("prefix"): cv.string,
            }
        )


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    username: str = config[CONF_USERNAME]
    password: str = config[CONF_PASSWORD]
    gateway: str = config[CONF_ID]
    if config["use_sn"]:
        unique_id = gateway
    else:
        unique_id = None
    if config["prefix"]:
        prefix = config["prefix"]
    else:
        prefix = "FranklinWH"

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)
    cache = ThreadedCachingClient(client)

    add_entities([
        FranklinBatterySensor(cache, prefix, unique_id),
        HomeLoadSensor(cache, prefix, unique_id),
        BatteryUseSensor(cache, prefix, unique_id),
        GridUseSensor(cache, prefix, unique_id),
        SolarProductionSensor(cache, prefix, unique_id),
        BatteryChargeSensor(cache, prefix, unique_id),
        BatteryDischargeSensor(cache, prefix, unique_id),
        GeneratorUseSensor(cache, prefix, unique_id),
        GridImportSensor(cache, prefix, unique_id),
        GridExportSensor(cache, prefix, unique_id),
        SolarEnergySensor(cache, prefix, unique_id),
        Sw1LoadSensor(cache, prefix, unique_id),
        Sw1UseSensor(cache, prefix, unique_id),
        Sw2LoadSensor(cache, prefix, unique_id),
        Sw2UseSensor(cache, prefix, unique_id),
        V2LUseSensor(cache, prefix, unique_id),
        V2LExportSensor(cache, prefix, unique_id),
        V2LImportSensor(cache, prefix, unique_id),
        ])

UPDATE_INTERVAL = 60

class ThreadedCachingClient(object):
    def __init__(self, client):
        self.thread = franklinwh.CachingThread()
        self.thread.start(client.get_stats)

    def fetch(self):
        return self.thread.get_data()

class FranklinBatterySensor(SensorEntity):
    """Shows the current state of charge of the battery"""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " State of Charge"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_state_of_charge"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.battery_soc

class HomeLoadSensor(SensorEntity):
    """Shows the current power use by the home load"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Home Load"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_home_load"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.home_load

class HomeUseSensor(SensorEntity):
    """Shows the total energy used by the home"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Generator Energy"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_generator_energy"

    def update(self) -> None:
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.home_use

class GridUseSensor(SensorEntity):
    """Shows the current import or export from the grid"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Grid Use"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_grid_use"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.grid_use * -1

class GridImportSensor(SensorEntity):
    """Shows the amount of energy imported from the grid"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Grid Import"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_grid_import"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.grid_import

class GridExportSensor(SensorEntity):
    """Shows the amount of energy exported to the grid"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Grid Export"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_grid_export"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.grid_export

class SolarProductionSensor(SensorEntity):
    """Shows the current solar production"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Solar Production"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_solar_production"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.solar_production

class SolarEnergySensor(SensorEntity):
    """Shows the energy generated by solar"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Solar Energy"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_solar_energy"

    def update(self) -> None:
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.solar

class BatteryUseSensor(SensorEntity):
    """Shows the current charge or discharge from the battery"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Battery Use"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_batter_use"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.battery_use * -1


class BatteryChargeSensor(SensorEntity):
    """Shows the charging stats of the battery"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Battery Charge"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_battery_charge"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.battery_charge

class BatteryDischargeSensor(SensorEntity):
    """Shows the charging stats of the battery"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Battery Discharge"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_battery_discharge"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.battery_discharge

class GeneratorUseSensor(SensorEntity):
    """Shows the current power output of the generator"""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Generator Use"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_generator_use"

    def update(self) -> None:
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.generator_production

class GeneratorEnergySensor(SensorEntity):
    """Shows the energy imported from the generator"""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Generator Energy"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_generator_energy"

    def update(self) -> None:
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.generator

class Sw1LoadSensor(SensorEntity):
    """Shows the current power use by switch 1"""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Switch 1 Load"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_switch_1_load"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.switch_1_load

class Sw1UseSensor(SensorEntity):
    """Shows the lifetime energy usage by switch 1"""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Switch 1 Lifetime Use"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "switch_1_lifetime_use"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.switch_1_use


class Sw2LoadSensor(SensorEntity):
    """Shows the current power use by switch 2"""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Switch 2 Load"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_switch_2_load"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.switch_2_load

class Sw2UseSensor(SensorEntity):
    """Shows the lifetime energy usage by switch 1"""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " Switch 2 Lifetime Use"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_switch_2_lifetime_use"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.switch_2_use


class V2LUseSensor(SensorEntity):
    """Shows the current power use by the car switch"""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " V2L Use"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_v2l_use"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.v2l_use

class V2LExportSensor(SensorEntity):
    """Shows the lifetime energy exported to the car switch"""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " V2L Export"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_v2l_export"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.v2l_export

class V2LImportSensor(SensorEntity):
    """Shows the lifetime energy exported to the car switch"""

    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, prefix, unique_id):
        self._cache = cache
        self._attr_name = prefix + " V2L Import"
        if unique_id:
            self.__attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_v2l_import"

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.v2l_import
