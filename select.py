#!/usr/bin/env python
import franklinwh
from collections.abc import Callable, Hashable
from typing import Any

from homeassistant.components.select import (
    SelectEntity,
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
        CONF_USERNAME,
        CONF_PASSWORD,
        CONF_ID,
        CONF_SWITCHES,
        )

MODES = {
        "time_of_use": franklinwh.Mode.time_of_use,
        "emergency_backup": franklinwh.Mode.emergency_backup,
        "self_consumption": franklinwh.Mode.self_consumption,
        }


def dict_validator(
    keys: list[str],
    values: vol.Schema,
) -> Callable[[Any], dict[Hashable, Any]]:
    """Create a validator that a dict's keys are in an allowlist, and whose values conform to a schema.
    """

    def dict_validator(value: Any) -> dict[Hashable, Any]:
        if not isinstance(value, dict):
            raise vol.Invalid("Expected a dictionary")

        for k, v in value.items():
            vol.In(keys)(k)
            values(v)

        return value

    return dict_validator

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Required(CONF_ID): cv.string,
            "modes": vol.All(
                {
                    vol.Optional("time_of_use"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                    vol.Optional("emergency_backup"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                    vol.Optional("self_consumption"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                },
                cv.has_at_least_one_key("time_of_use", "emergency_backup", "self_consumption")
                )
        }
    )

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    username: str = config[CONF_USERNAME]
    password: str = config[CONF_PASSWORD]
    gateway: str = config[CONF_ID]
    modes: dict[str, int] = config["modes"]

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)

    add_entities([
        ModeSelect(modes, client),
        ])

class ModeSelect(SelectEntity):
    def __init__(self, modes, client):
        self.modes = modes
        self._current_option = None
        self._attr_name = "FranklinWH Mode"
        self.client = client

    @property
    def current_option(self) -> str:
        return self._current_option

    @property
    def options(self) -> list[str]:
        return list(self.modes.keys())

    def update(self):
        (name, soc) = self.client.get_mode()
        self._current_option = name

    def select_option(self, option: str):
        mode = MODES[option](self.modes[option])
        self.client.set_mode(mode)
        self._current_option = option


