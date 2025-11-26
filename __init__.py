"""The FranklinWH integration.

Complete rewrite by Joshua Seidel (@JoshuaSeidel) with Anthropic Claude Sonnet 4.5.
Originally inspired by @richo's homeassistant-franklinwh integration.
Uses the franklinwh-python library by @richo.

set_mode service implementation based on @j4m3z0r's working fork.
"""
from __future__ import annotations

import logging

import franklinwh
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
import voluptuous as vol

from .const import (
    CONF_GATEWAY_ID,
    CONF_LOCAL_HOST,
    CONF_USE_LOCAL_API,
    DOMAIN,
)
from .coordinator import FranklinWHCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

SERVICE_SET_MODE = "set_mode"

# Mode mapping from j4m3z0r's implementation
MODE_MAP = {
    "Self Consumption": franklinwh.Mode.self_consumption,
    "Time of Use": franklinwh.Mode.time_of_use,
    "Emergency Backup": franklinwh.Mode.emergency_backup,
}


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

    # Register service
    async def handle_set_mode(call: ServiceCall) -> None:
        """Handle the set_mode service call.
        
        Implementation based on j4m3z0r's working fork.
        """
        entity_id = call.data["entity_id"]
        mode_name = call.data["mode"]
        soc = call.data.get("soc")

        _LOGGER.debug(
            "set_mode service called for entity %s, mode %s, soc %s",
            entity_id,
            mode_name,
            soc,
        )

        # Find the coordinator for this entity
        entity_reg = er.async_get(hass)
        entity_entry = entity_reg.async_get(entity_id)
        
        if not entity_entry:
            _LOGGER.error("Entity %s not found in entity registry", entity_id)
            return

        # Find coordinator by checking config entry
        target_coordinator = None
        for entry_id, coord in hass.data[DOMAIN].items():
            if isinstance(coord, FranklinWHCoordinator):
                if entity_entry.config_entry_id == entry_id:
                    target_coordinator = coord
                    break

        if not target_coordinator:
            _LOGGER.error("Could not find FranklinWH device for entity %s", entity_id)
            return

        # Check if franklinwh.Mode exists
        if not hasattr(franklinwh, 'Mode'):
            _LOGGER.error(
                "franklinwh.Mode class not found. Your franklinwh library version "
                "does not support mode changes. Please update to version 0.6.0 or newer."
            )
            return

        # Get the mode function from the map
        mode_function = MODE_MAP.get(mode_name)
        if not mode_function:
            _LOGGER.error("Invalid mode '%s' specified", mode_name)
            return

        # Create mode object (with or without SOC)
        if soc is None:
            mode = mode_function()
        else:
            mode = mode_function(soc)

        try:
            _LOGGER.debug(
                "Calling set_mode on client for gateway %s with mode %s",
                target_coordinator.gateway_id,
                mode,
            )
            
            # Call set_mode using the coordinator's method
            await target_coordinator.async_set_mode_direct(mode)
            
            _LOGGER.info(
                "Successfully set mode to '%s' for gateway %s",
                mode_name,
                target_coordinator.gateway_id
            )
        except Exception as err:
            _LOGGER.error(
                "Error setting mode for gateway %s: %s",
                target_coordinator.gateway_id,
                err
            )

    # Register service only once
    if not hass.services.has_service(DOMAIN, SERVICE_SET_MODE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_MODE,
            handle_set_mode,
            schema=vol.Schema(
                {
                    vol.Required("entity_id"): vol.Any(str, [str]),
                    vol.Required("mode"): vol.In(
                        ["Time of Use", "Self Consumption", "Emergency Backup"]
                    ),
                    vol.Optional("soc"): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=100)
                    ),
                }
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
