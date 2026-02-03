"""Sensor platform for FranklinWH integration."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
import logging

from franklinwh import AccessoryType
from franklinwh.client import Stats

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GATEWAY_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FranklinWHCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FranklinWHSensorEntityDescription(SensorEntityDescription):
    """Describes FranklinWH sensor entity."""

    value_fn: Callable[[Stats], float | int | None] | None = None


GENERIC_SENSORS: tuple[FranklinWHSensorEntityDescription, ...] = (
    FranklinWHSensorEntityDescription(
        key="battery_soc",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.battery_soc,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_use",
        name="Battery Use",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.battery_use * -1,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_charge",
        name="Battery Charge",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: stats.totals.battery_charge,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_discharge",
        name="Battery Discharge",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: stats.totals.battery_discharge,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_charge_from_grid",
        name="Battery Charge from Grid",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: (
            # Battery charged from grid = Total battery charge - Solar energy
            # (assuming all solar goes to battery first, excess goes to home/grid)
            max(0, (stats.totals.battery_charge or 0) - (stats.totals.solar or 0))
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="home_load",
        name="Home Load",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.home_load,
    ),
    FranklinWHSensorEntityDescription(
        key="home_use",
        name="Home Use",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: stats.totals.home_use,
    ),
    FranklinWHSensorEntityDescription(
        key="grid_use",
        name="Grid Use",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.grid_use * -1,
    ),
    FranklinWHSensorEntityDescription(
        key="grid_import",
        name="Grid Import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: stats.totals.grid_import,
    ),
    FranklinWHSensorEntityDescription(
        key="grid_export",
        name="Grid Export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: stats.totals.grid_export,
    ),
    FranklinWHSensorEntityDescription(
        key="solar_production",
        name="Solar Production",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.solar_production,
    ),
    FranklinWHSensorEntityDescription(
        key="solar_energy",
        name="Solar Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: stats.totals.solar,
    ),
)
GENERATOR_SENSORS: tuple[FranklinWHSensorEntityDescription, ...] = (
    FranklinWHSensorEntityDescription(
        key="generator_use",
        name="Generator Use",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.generator_production,
    ),
    FranklinWHSensorEntityDescription(
        key="generator_energy",
        name="Generator Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: stats.totals.generator,
    ),
)
SMART_CIRCUIT_SENSORS: tuple[FranklinWHSensorEntityDescription, ...] = (
    FranklinWHSensorEntityDescription(
        key="switch_1_load",
        name="Switch 1 Load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.switch_1_load,
    ),
    FranklinWHSensorEntityDescription(
        key="switch_1_lifetime_use",
        name="Switch 1 Lifetime Use",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: (stats.totals.switch_1_use / 1000),
    ),
    FranklinWHSensorEntityDescription(
        key="switch_2_load",
        name="Switch 2 Load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.switch_2_load,
    ),
    FranklinWHSensorEntityDescription(
        key="switch_2_lifetime_use",
        name="Switch 2 Lifetime Use",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: (stats.totals.switch_2_use / 1000),
    ),
    FranklinWHSensorEntityDescription(
        key="v2l_use",
        name="V2L Use",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stats: stats.current.v2l_use,
    ),
    FranklinWHSensorEntityDescription(
        key="v2l_export",
        name="V2L Export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: (stats.totals.v2l_export / 1000),
    ),
    FranklinWHSensorEntityDescription(
        key="v2l_import",
        name="V2L Import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda stats: (stats.totals.v2l_import / 1000),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FranklinWH sensors."""
    coordinator: FranklinWHCoordinator = hass.data[DOMAIN][entry.entry_id]

    def _entities(
        descriptions: Iterable[FranklinWHSensorEntityDescription],
    ) -> Iterator[FranklinWHSensorEntity]:
        for description in descriptions:
            yield FranklinWHSensorEntity(coordinator, description, entry)

    entities = list(_entities(GENERIC_SENSORS))

    accessories = await coordinator.client.get_accessories()
    coordinator.logger.debug("Accessories: %s", accessories)

    for accessory in accessories:
        try:
            match accessory["accessoryType"]:
                case AccessoryType.SMART_CIRCUIT_MODULE.value:
                    entities.extend(_entities(SMART_CIRCUIT_SENSORS))
                case AccessoryType.GENERATOR_MODULE.value:
                    entities.extend(_entities(GENERATOR_SENSORS))
        except KeyError as err:
            coordinator.logger.error("Expected key 'accessoryType' not found: %s", err)

    async_add_entities(entities)


class FranklinWHSensorEntity(CoordinatorEntity[FranklinWHCoordinator], SensorEntity):
    """Representation of a FranklinWH sensor."""

    entity_description: FranklinWHSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FranklinWHCoordinator,
        description: FranklinWHSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        gateway_id = entry.data[CONF_GATEWAY_ID]

        # Set unique ID
        self._attr_unique_id = f"{gateway_id}_{description.key}"

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"FranklinWH {gateway_id[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=entry.data.get("sw_version"),
        )

    @property
    def native_value(self) -> float | int | None:
        """Return the state of the sensor."""
        if (
            self.entity_description.value_fn is None
            or self.coordinator.data is None
            or self.coordinator.data.stats is None
        ):
            return None

        try:
            return self.entity_description.value_fn(self.coordinator.data.stats)
        except (AttributeError, TypeError, KeyError) as err:
            _LOGGER.debug(
                "Error getting value for %s: %s", self.entity_description.key, err
            )
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.stats is not None
        )
