"""The FranklinWH integration.

Portions adapted from @JoshuaSeidel fork.
Uses the franklinwh-python library by @richo.
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_GATEWAY_ID, CONF_LOCAL_HOST, CONF_USE_LOCAL_API, DOMAIN
from .coordinator import FranklinWHCoordinator
from .utils import get_client

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FranklinWH from a config entry."""

    _, client = await get_client(
        hass,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_GATEWAY_ID],
    )

    coordinator = FranklinWHCoordinator(
        hass=hass,
        client=client,
        use_local_api=entry.data.get(CONF_USE_LOCAL_API, False),
        local_host=entry.data.get(CONF_LOCAL_HOST),
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed as err:
        coordinator.logger.error("Authentication failed: %s", err)
        raise
    except Exception as err:
        coordinator.logger.error("Error setting up FranklinWH: %s", err)
        raise ConfigEntryNotReady from err

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
