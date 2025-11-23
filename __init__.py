"""The FranklinWH integration."""
import logging
import franklinwh

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.typing import ConfigType

DOMAIN = "franklin_wh"
_LOGGER = logging.getLogger(__name__)

MODE_MAP = {
    "Self Consumption": franklinwh.Mode.self_consumption,
    "Time of Use": franklinwh.Mode.time_of_use,
    "Emergency Backup": franklinwh.Mode.emergency_backup,
}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the FranklinWH integration."""

    KNOWN_SUFFIXES = [
        "_state_of_charge", "_home_load", "_home_use", "_grid_use", 
        "_grid_import", "_grid_export", "_solar_production", "_solar_energy",
        "_battery_use", "_battery_charge", "_battery_discharge",
        "_generator_use", "_generator_energy", "_switch_1_load",
        "_switch_1_lifetime_use", "_switch_2_load", "_switch_2_lifetime_use",
        "_v2l_use", "_v2l_export", "_v2l_import"
    ]

    async def async_set_mode(call: ServiceCall) -> None:
        """Handle mode change service calls."""
        entity_id = call.data.get("entity_id")
        mode_name = call.data.get("mode")
        soc = call.data.get("soc")

        _LOGGER.debug(
            "set_mode service called for entity %s, mode %s, soc %s",
            entity_id,
            mode_name,
            soc,
        )

        ent_reg = entity_registry.async_get(hass)
        entity = ent_reg.async_get(entity_id)
        if not entity:
            _LOGGER.error("Entity '%s' not found in entity registry.", entity_id)
            return

        gateway_id = None
        unique_id = entity.unique_id

        for suffix in KNOWN_SUFFIXES:
            if unique_id.endswith(suffix):
                gateway_id = unique_id[: -len(suffix)]
                break
        
        if not gateway_id:
            _LOGGER.error(
                "Could not determine gateway ID from entity '%s' with unique_id: %s",
                entity_id,
                entity.unique_id,
            )
            return

        _LOGGER.debug("Found gateway ID '%s' from entity '%s'", gateway_id, entity_id)

        client = hass.data[DOMAIN].get(gateway_id, {}).get("client")
        if not client:
            _LOGGER.error("FranklinWH client not found for gateway %s.", gateway_id)
            return

        mode_function = MODE_MAP.get(mode_name)
        if not mode_function:
            _LOGGER.error("Invalid mode '%s' specified.", mode_name)
            return

        if soc is None:
            mode = mode_function()
        else:
            mode = mode_function(soc)

        try:
            _LOGGER.debug(
                "Calling set_mode on client for gateway %s with mode %s",
                gateway_id,
                mode,
            )
            await hass.async_add_executor_job(client.set_mode, mode)
            _LOGGER.info(
                "Successfully set mode to '%s' for gateway %s", mode_name, gateway_id
            )
        except Exception as e:
            _LOGGER.error("Error setting mode for gateway %s: %s", gateway_id, e)

    hass.services.async_register(
        DOMAIN,
        "set_mode",
        async_set_mode,
    )

    return True

