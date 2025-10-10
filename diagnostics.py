"""Diagnostics support for FranklinWH."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_GATEWAY_ID, DOMAIN
from .coordinator import FranklinWHCoordinator

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME, CONF_GATEWAY_ID, "token", "access_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: FranklinWHCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    diagnostics_data = {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
        },
        "coordinator_data": await _async_get_coordinator_diagnostics(coordinator),
    }
    
    return diagnostics_data


async def _async_get_coordinator_diagnostics(
    coordinator: FranklinWHCoordinator,
) -> dict[str, Any]:
    """Get diagnostics for the coordinator."""
    if coordinator.data is None:
        return {"error": "No data available"}
    
    diagnostics = {
        "last_update_success": coordinator.last_update_success,
        "last_update_time": coordinator.last_update_success_time.isoformat()
        if coordinator.last_update_success_time
        else None,
        "update_interval": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
    }
    
    # Add stats data if available
    if coordinator.data.stats:
        try:
            stats = coordinator.data.stats
            diagnostics["stats"] = {
                "current": {
                    "battery_soc": getattr(stats.current, "battery_soc", None),
                    "battery_use": getattr(stats.current, "battery_use", None),
                    "home_load": getattr(stats.current, "home_load", None),
                    "grid_use": getattr(stats.current, "grid_use", None),
                    "solar_production": getattr(stats.current, "solar_production", None),
                    "generator_production": getattr(
                        stats.current, "generator_production", None
                    ),
                    "switch_1_load": getattr(stats.current, "switch_1_load", None),
                    "switch_2_load": getattr(stats.current, "switch_2_load", None),
                    "v2l_use": getattr(stats.current, "v2l_use", None),
                },
                "totals": {
                    "battery_charge": getattr(stats.totals, "battery_charge", None),
                    "battery_discharge": getattr(stats.totals, "battery_discharge", None),
                    "grid_import": getattr(stats.totals, "grid_import", None),
                    "grid_export": getattr(stats.totals, "grid_export", None),
                    "solar": getattr(stats.totals, "solar", None),
                    "generator": getattr(stats.totals, "generator", None),
                    "switch_1_use": getattr(stats.totals, "switch_1_use", None),
                    "switch_2_use": getattr(stats.totals, "switch_2_use", None),
                    "v2l_export": getattr(stats.totals, "v2l_export", None),
                    "v2l_import": getattr(stats.totals, "v2l_import", None),
                },
            }
        except Exception as err:
            diagnostics["stats_error"] = str(err)
    
    # Add switch state data if available
    if coordinator.data.switch_state:
        diagnostics["switch_state"] = {
            "switch_1": coordinator.data.switch_state[0]
            if len(coordinator.data.switch_state) > 0
            else None,
            "switch_2": coordinator.data.switch_state[1]
            if len(coordinator.data.switch_state) > 1
            else None,
            "switch_3": coordinator.data.switch_state[2]
            if len(coordinator.data.switch_state) > 2
            else None,
        }
    
    return diagnostics

