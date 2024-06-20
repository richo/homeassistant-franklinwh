#!/usr/bin/env python

import franklinwh

from homeassistant.components.switch import (
    SwitchEntity,
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
)
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
        CONF_ACCESS_TOKEN,
        CONF_ID,
        CONF_NAME,
        CONF_SWITCHES,
        )
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
            vol.Required(CONF_SWITCHES): cv.ensure_list(vol.In([1, 2, 3])),
            }
        )

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    access_token: str = config[CONF_ACCESS_TOKEN]
    gateway: str = config[CONF_ID]
    name: str = config[CONF_NAME]

    switches: list[int] = list(map(lambda x: x-1, config[CONF_SWITCHES]))

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)
    cache = CachingClient(client.get_stats)

    add_entities([
        SmartCircuitSwitch(name, switches, client),
        ])

# Is it chill to have a switch in here? We'll see!
class SmartCircuitSwitch(SwitchEntity):
    def __init__(self, name, switches, client):
        self._is_on = False
        self.switches = switches
        self._attr_name = "FranklinWH {}".format(name)
        self.client = client

    def update(self):
        pass

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self._is_on

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._is_on = True

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._is_on = False
