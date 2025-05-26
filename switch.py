#!/usr/bin/env python

import franklinwh

from homeassistant.components.switch import (
    SwitchEntity,
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
    username: str = config[CONF_USERNAME]
    password: str = config[CONF_PASSWORD]
    gateway: str = config[CONF_ID]
    name: str = config[CONF_NAME]

    switches: list[int] = list(map(lambda x: x-1, config[CONF_SWITCHES]))

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)

    add_entities([
        SmartCircuitSwitch(name, switches, client),
        ])

class ThreadedCachingClient(object):
    def __init__(self, client):
        self.thread = franklinwh.CachingThread()
        self.thread.start(client.get_smart_switch_state)

    def fetch(self):
        return self.thread.get_data()

# Is it chill to have a switch in here? We'll see!
class SmartCircuitSwitch(SwitchEntity):
    def __init__(self, name, switches, client):
        self._is_on = False
        self.switches = switches
        self._attr_name = "FranklinWH {}".format(name)
        self.client = client
        self.cache = ThreadedCachingClient(client)

    def update(self):
        state = self.cache.fetch()
        if state is None:
            # Cache hasn't populated yet
            return
        values = list(map(lambda x: state[x], self.switches))
        if all(values):
            self._is_on = True
        elif all(map(lambda x: x is False, values)):
            self._is_on = False
        else:
            # Something's fucky!
            self._is_on = None

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self._is_on

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        switches = [None, None, None]
        for i in self.switches:
            switches[i] = True
        self.client.set_smart_switch_state(switches)

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        switches = [None, None, None]
        for i in self.switches:
            switches[i] = False
        self.client.set_smart_switch_state(switches)
