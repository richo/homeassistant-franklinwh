"""Number platform for FranklinWH integration."""

from homeassistant.components.number import NumberEntity
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
    entities: list[NumberEntity] = [BackupReserve(coordinator, entry)]

    coordinator.enable("mode")
    await coordinator.async_config_entry_first_refresh()
    async_add_entities(entities)


class BackupReserve(CoordinatorEntity[FranklinWHCoordinator], NumberEntity):
    """Representation of the FranklinWH backup reserve percentage."""

    _attr_has_entity_name = True
    _attr_min_value = 5  # pyright: ignore[reportAssignmentType]
    _attr_max_value = 100  # pyright: ignore[reportAssignmentType]
    _attr_step = 1  # pyright: ignore[reportAssignmentType]
    _attr_unit_of_measurement = "%"  # pyright: ignore[reportAssignmentType]

    def __init__(
        self,
        coordinator: FranklinWHCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the backup reserve number entity."""
        super().__init__(coordinator)

        gateway_id = entry.data[CONF_GATEWAY_ID]

        # Set unique ID
        self._attr_unique_id = f"{gateway_id}_backup_reserve"

        # Set name
        self._attr_name = "Backup Reserve"

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"FranklinWH {gateway_id[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=entry.data.get("sw_version"),
        )

    @property
    def value(self) -> float | None:
        """Return the current backup reserve percentage."""
        if self.coordinator.data is None or self.coordinator.data.mode is None:
            return None
        return float(self.coordinator.data.mode.soc)

    @property
    def icon(self) -> str:
        """Return the icon for the backup reserve percentage."""
        value = self.value
        if value is None:
            return "mdi:battery-alert"
        if value >= 99:
            return "mdi:battery"
        if value < 10:
            return "mdi:battery-outline"
        return "mdi:battery-" + str(int(value // 10 * 10))

    async def async_set_native_value(self, value: float) -> None:
        """Set the backup reserve percentage."""
        await self.coordinator.async_set_backup_reserve(int(value))
