"""Switch platform for FranklinWH integration."""

from __future__ import annotations

import logging
from typing import Any

from franklinwh import AccessoryType, GridStatus

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GATEWAY_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FranklinWHCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FranklinWH switches."""
    coordinator: FranklinWHCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [GridSwitch(coordinator, entry)]

    await coordinator.async_config_entry_first_refresh()
    accessories = await coordinator.client.get_accessories()
    _LOGGER.debug("Accessories: %s", accessories)

    for accessory in accessories:
        try:
            match accessory["accessoryType"]:
                case AccessoryType.SMART_CIRCUIT_MODULE.value:
                    entities.extend(
                        FranklinWHSmartSwitch(coordinator, entry, switch_id)
                        for switch_id in range(3)
                    )
        except KeyError as err:
            _LOGGER.error("Expected key 'accessoryType' not found: %s", err)

    async_add_entities(entities)


class FranklinWHSmartSwitch(CoordinatorEntity[FranklinWHCoordinator], SwitchEntity):
    """Representation of a FranklinWH smart circuit switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FranklinWHCoordinator,
        entry: ConfigEntry,
        switch_id: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)

        self._switch_id = switch_id
        self._switch_index = switch_id  # 0-indexed for API
        gateway_id = entry.data[CONF_GATEWAY_ID]

        # Set unique ID
        self._attr_unique_id = f"{gateway_id}_switch_{switch_id + 1}"

        # Set name
        self._attr_name = f"Switch {switch_id + 1}"

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"FranklinWH {gateway_id[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=entry.data.get("sw_version"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self.coordinator.data is None or self.coordinator.data.switch_state is None:
            return None

        try:
            return self.coordinator.data.switch_state[self._switch_index]
        except (IndexError, TypeError):
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.switch_state is not None
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        switches = [None, None, None]
        switches[self._switch_index] = True

        try:
            await self.coordinator.async_set_switch_state(switches)
        except Exception as err:
            _LOGGER.error("Failed to turn on switch %d: %s", self._switch_id + 1, err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        switches = [None, None, None]
        switches[self._switch_index] = False

        try:
            await self.coordinator.async_set_switch_state(switches)
        except Exception as err:
            _LOGGER.error("Failed to turn off switch %d: %s", self._switch_id + 1, err)
            raise

    @property
    def icon(self) -> str:
        """Return the icon for the switch."""
        if self.is_on:
            return "mdi:electric-switch-closed"
        return "mdi:electric-switch"


class GridSwitch(CoordinatorEntity[FranklinWHCoordinator], SwitchEntity):
    """Representation of the grid connection switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FranklinWHCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the grid switch."""
        super().__init__(coordinator)

        gateway_id = entry.data[CONF_GATEWAY_ID]

        # Set unique ID
        self._attr_unique_id = f"{gateway_id}_grid_switch"

        # Set name
        self._attr_name = "Grid Connection"

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"FranklinWH {gateway_id[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=entry.data.get("sw_version"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the grid connection is on."""
        if self.coordinator.data is None or self.coordinator.data.stats is None:
            return None

        match self.coordinator.data.stats.current.grid_status:
            case GridStatus.NORMAL:
                return True
            case GridStatus.OFF:
                return False
            case _:
                return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.stats is not None
            and self.coordinator.data.stats.current.grid_status is not None
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the grid connection on."""
        try:
            await self.coordinator.client.set_grid_status(GridStatus.NORMAL)
            # TODO: the system takes a good while to switch states fully and reflect in the UI
        except Exception as err:
            _LOGGER.error("Failed to turn on grid connection: %s", err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the grid connection off."""
        try:
            await self.coordinator.client.set_grid_status(GridStatus.OFF)
            # TODO: the system takes a good while to switch states fully and reflect in the UI
        except Exception as err:
            _LOGGER.error("Failed to turn off grid connection: %s", err)
            raise

    @property
    def icon(self) -> str:
        """Return the icon for the switch."""
        if self.is_on:
            return "mdi:transmission-tower"
        return "mdi:transmission-tower-off"
