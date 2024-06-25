#!/usr/bin/env python
import franklinwh

from homeassistant.components.select import (
    SelectEntity,
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
)

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
        CONF_USERNAME,
        CONF_PASSWORD,
        CONF_ID,
        CONF_NAME,
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

        vol.In(keys)(value.keys())
        values(value.values())

    return key_value_validator

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
            vol.Required("modes"): cv.dict_validator(
                MODES.keys(),
                vol.All(vol.Coerce(int), vol.Range(min=0, max=100))
                ),
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
    name: str = config[CONF_NAME]
    modes = config["modes"]

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)

    add_entities([
        ModeSelect(name, modes, client),
        ])

class SmartCircuitSwitch(SwitchEntity):
    def __init__(self, name, modes, client):
        self.modes = modes
        self.current_option = "self_consumption"
        self._attr_name = "FranklinWH Mode"
        self.client = client

    @property
    def current_option(self) -> str:
        return self._current_option

    @property
    def options(self) -> List[str]:
        return MODES.keys()

    def update(self):
        pass

    def select_option(self, option: str):
        mode = MODES[option](self.modes[option])
        client.set_mode(mode)


