"""The FranklinWH integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
import voluptuous as vol

from .const import (
    CONF_GATEWAY_ID,
    CONF_LOCAL_HOST,
    CONF_USE_LOCAL_API,
    DOMAIN,
    SERVICE_SET_BATTERY_RESERVE,
    SERVICE_SET_OPERATION_MODE,
)
from .coordinator import FranklinWHCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FranklinWH from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    gateway_id = entry.data[CONF_GATEWAY_ID]
    use_local_api = entry.data.get(CONF_USE_LOCAL_API, False)
    local_host = entry.data.get(CONF_LOCAL_HOST)

    # Create coordinator
    coordinator = FranklinWHCoordinator(
        hass=hass,
        username=username,
        password=password,
        gateway_id=gateway_id,
        use_local_api=use_local_api,
        local_host=local_host,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise
    except Exception as err:
        _LOGGER.error("Error setting up FranklinWH: %s", err)
        raise ConfigEntryNotReady from err

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def handle_set_operation_mode(call: ServiceCall) -> None:
        """Handle the set_operation_mode service call."""
        mode = call.data.get("mode")
        try:
            await coordinator.async_set_operation_mode(mode)
        except NotImplementedError:
            _LOGGER.warning("Operation mode control not yet available in API")

    async def handle_set_battery_reserve(call: ServiceCall) -> None:
        """Handle the set_battery_reserve service call."""
        reserve_percent = call.data.get("reserve_percent")
        try:
            await coordinator.async_set_battery_reserve(reserve_percent)
        except NotImplementedError:
            _LOGGER.warning("Battery reserve control not yet available in API")

    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_SET_OPERATION_MODE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_OPERATION_MODE,
            handle_set_operation_mode,
            schema=vol.Schema(
                {
                    vol.Required("mode"): vol.In(
                        ["self_use", "backup", "time_of_use", "clean_backup"]
                    )
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_BATTERY_RESERVE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_BATTERY_RESERVE,
            handle_set_battery_reserve,
            schema=vol.Schema(
                {vol.Required("reserve_percent"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))}
            ),
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
