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
        CONF_ACCESS_TOKEN,
        CONF_ID,
        )

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_ACCESS_TOKEN): cv.string,
            vol.Required(CONF_ID): cv.string,
            }
        )


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    access_token: str = config[CONF_ACCESS_TOKEN]
    gateway: str = config[CONF_ID]

    client = franklinwh.Client(access_token, gateway)
    cache = CachingClient(client.get_stats)

    add_entities([
        FranklinBatterySensor(cache),
        HomeLoadSensor(cache),
        BatteryUseSensor(cache),
        GridUseSensor(cache),
        SolarProductionSensor(cache),
        ])

UPDATE_INTERVAL = 15 * 60
class CachingClient(object):
    def __init__(self, update_func):
        self.mutex = Lock()
        self.update_func = update_func
        self.last_fetched = 0
        self.data = None

    def _fetch(self):
        self.data = self.update_func()

    def fetch(self):
        with self.mutex:
            now = time.monotonic()
            if now > self.last_fetched + UPDATE_INTERVAL:
                self.last_fetched = now
                self._fetch()
            return self.data

# TODO(richo) Figure out how to have a singleton cache for the franklin data

class FranklinBatterySensor(SensorEntity):
    """Shows the current state of charge of the battery"""

    _attr_name = "franklinwh state of charge"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache):
        self._cache = cache

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        self._attr_native_value = stats.current.battery_soc

class HomeLoadSensor(SensorEntity):
    """Shows the current state of charge of the battery"""

    _attr_name = "franklinwh home load"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache):
        self._cache = cache

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        self._attr_native_value = stats.current.home_load

class BatteryUseSensor(SensorEntity):
    """Shows the current state of charge of the battery"""

    _attr_name = "franklinwh battery use"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache):
        self._cache = cache

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        self._attr_native_value = stats.current.battery_use

class GridUseSensor(SensorEntity):
    """Shows the current state of charge of the battery"""

    _attr_name = "franklinwh grid use"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache):
        self._cache = cache

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        self._attr_native_value = stats.current.grid_use

class SolarProductionSensor(SensorEntity):
    """Shows the current state of charge of the battery"""

    _attr_name = "franklinwh solar production"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, cache):
        self._cache = cache

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        stats = self._cache.fetch()
        self._attr_native_value = stats.current.solar_production


