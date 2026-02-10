"""Select platform for FranklinWH integration."""

from franklinwh import Mode

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GATEWAY_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FranklinWHCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FranklinWH selectors."""
    coordinator: FranklinWHCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = [ModeSelect(coordinator, entry)]

    coordinator.enable("mode")
    await coordinator.async_config_entry_first_refresh()
    async_add_entities(entities)


class ModeSelect(CoordinatorEntity[FranklinWHCoordinator], SelectEntity):
    """Representation of the FranklinWH operating mode."""

    _attr_has_entity_name = True
    _attr_options = list(Mode.NAMES.values())
    _icons = {
        Mode.TIME_OF_USE_NAME: "mdi:battery-clock",
        Mode.SELF_CONSUMPTION_NAME: "mdi:battery-arrow-down",
        Mode.EMERGENCY_BACKUP_NAME: "mdi:battery-arrow-up",
        Mode.VPP_MODE_NAME: "mdi:battery-heart",
        None: "mdi:battery-alert",
    }
    assert set(_icons.keys()) == set(_attr_options) | {None}

    def __init__(
        self,
        coordinator: FranklinWHCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the mode select."""
        super().__init__(coordinator)

        gateway_id = entry.data[CONF_GATEWAY_ID]

        # Set unique ID
        self._attr_unique_id = f"{gateway_id}_mode"

        # Set name
        self._attr_name = "Operating Mode"

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"FranklinWH {gateway_id[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=entry.data.get("sw_version"),
        )

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if self.coordinator.data is None or self.coordinator.data.mode is None:
            return None
        return self.coordinator.data.mode.name

    @property
    def icon(self) -> str:
        """Return the icon for the select."""
        return self._icons[self.current_option]

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        await self.coordinator.async_set_mode(option)
