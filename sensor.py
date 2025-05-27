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
            vol.Optional("multiple"): cv.bool,
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
    if config["multiple"]:
        unique_id = gateway
    else:
        unique_id = None

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)
    cache = ThreadedCachingClient(client)

    add_entities([
        FranklinBatterySensor(cache, unique_id),
        HomeLoadSensor(cache, unique_id),
        BatteryUseSensor(cache, unique_id),
        GridUseSensor(cache, unique_id),
        SolarProductionSensor(cache, unique_id),
        BatteryChargeSensor(cache, unique_id),
        BatteryDischargeSensor(cache, unique_id),
        GeneratorUseSensor(cache, unique_id),
        GridImportSensor(cache, unique_id),
        GridExportSensor(cache, unique_id),
        SolarEnergySensor(cache, unique_id),
        Sw1LoadSensor(cache, unique_id),
        Sw1UseSensor(cache, unique_id),
        Sw2LoadSensor(cache, unique_id),
        Sw2UseSensor(cache, unique_id),
        V2LUseSensor(cache, unique_id),
        V2LExportSensor(cache, unique_id),
        V2LImportSensor(cache, unique_id),
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

    _attr_name = "FranklinWH State of Charge"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.battery_soc

class HomeLoadSensor(SensorEntity):
    """Shows the current power use by the home load"""

    _attr_name = "FranklinWH Home Load"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.home_load

class HomeUseSensor(SensorEntity):
    """Shows the total energy used by the home"""

    _attr_name = "FranklinWH Generator Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.home_use

class GridUseSensor(SensorEntity):
    """Shows the current import or export from the grid"""

    _attr_name = "FranklinWH Grid Use"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.grid_use * -1

class GridImportSensor(SensorEntity):
    """Shows the amount of energy imported from the grid"""

    _attr_name = "FranklinWH Grid Import"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.grid_import

class GridExportSensor(SensorEntity):
    """Shows the amount of energy exported to the grid"""

    _attr_name = "FranklinWH Grid Export"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.grid_export

class SolarProductionSensor(SensorEntity):
    """Shows the current solar production"""

    _attr_name = "FranklinWH Solar Production"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.solar_production

class SolarEnergySensor(SensorEntity):
    """Shows the energy generated by solar"""

    _attr_name = "FranklinWH Solar Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.solar

class BatteryUseSensor(SensorEntity):
    """Shows the current charge or discharge from the battery"""

    _attr_name = "FranklinWH Battery Use"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.battery_use * -1


class BatteryChargeSensor(SensorEntity):
    """Shows the charging stats of the battery"""

    _attr_name = "FranklinWH Battery Charge"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.battery_charge

class BatteryDischargeSensor(SensorEntity):
    """Shows the charging stats of the battery"""

    _attr_name = "FranklinWH Battery Discharge"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.battery_discharge

class GeneratorUseSensor(SensorEntity):
    """Shows the current power output of the generator"""

    _attr_name = "FranklinWH Generator Use"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.generator_production

class GeneratorEnergySensor(SensorEntity):
    """Shows the energy imported from the generator"""

    _attr_name = "FranklinWH Generator Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.generator

class Sw1LoadSensor(SensorEntity):
    """Shows the current power use by switch 1"""

    _attr_name = "FranklinWH Switch 1 Load"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.switch_1_load

class Sw1UseSensor(SensorEntity):
    """Shows the lifetime energy usage by switch 1"""

    _attr_name = "FranklinWH Switch 1 Lifetime Use"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.switch_1_use


class Sw2LoadSensor(SensorEntity):
    """Shows the current power use by switch 2"""

    _attr_name = "FranklinWH Switch 2 Load"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.switch_2_load

class Sw2UseSensor(SensorEntity):
    """Shows the lifetime energy usage by switch 1"""

    _attr_name = "FranklinWH Switch 2 Lifetime Use"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.switch_2_use


class V2LUseSensor(SensorEntity):
    """Shows the current power use by the car switch"""

    _attr_name = "FranklinWH V2L Use"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.current.v2l_use

class V2LExportSensor(SensorEntity):
    """Shows the lifetime energy exported to the car switch"""

    _attr_name = "FranklinWH V2L Export"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.v2l_export

class V2LImportSensor(SensorEntity):
    """Shows the lifetime energy exported to the car switch"""

    _attr_name = "FranklinWH V2L Import"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, cache, unique_id=None):
        self._cache = cache
        if unique_id:
            self._attr_unique_id = unique_id

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        if stats is not None:
            self._attr_native_value = stats.totals.v2l_import
