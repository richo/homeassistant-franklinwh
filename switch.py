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

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

import logging
_LOGGER = logging.getLogger(__name__)
DEFAULT_UPDATE_INTERVAL = 30

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
            vol.Required(CONF_SWITCHES): cv.ensure_list(vol.In([1, 2, 3])),
            vol.Optional("use_sn", default=False): cv.boolean,
            vol.Optional("prefix", default=False): cv.string,
            vol.Optional("update_interval", default=DEFAULT_UPDATE_INTERVAL): cv.time_period,
            }
        )

async def async_setup_platform(
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
    update_interval: timedelta = config["update_interval"]

    # TODO(richo) why does it string the default value
    if config["use_sn"] and config["use_sn"] != "False":
        unique_id = gateway
    else:
        unique_id = None

    # TODO(richo) why does it string the default value
    if config["prefix"] and config["prefix"] != "False":
        prefix = config["prefix"]
    else:
        prefix = "FranklinWH"


    switches: list[int] = list(map(lambda x: x-1, config[CONF_SWITCHES]))

    fetcher = franklinwh.TokenFetcher(username, password)
    client = franklinwh.Client(fetcher, gateway)

    async def _update_data():
        _LOGGER.debug("Fetching latest switch data from FranklinWH...")
        try:
            return await client.get_smart_switch_state()

        except franklinwh.client.DeviceTimeoutException as e:
            _LOGGER.warning("Error getting data from FranklinWH - Device Timeout: %s", e)
        except franklinwh.client.GatewayOfflineException as e:
            _LOGGER.warning("Error getting data from FranklinWH - Gateway Offline %s", e)
        except franklinwh.client.AccountLockedException as e:
            _LOGGER.warning("Error getting data from FranklinWH - Account Locked %s", e)
        except franklinwh.client.InvalidCredentialsException as e:
            _LOGGER.warning("Error getting data from FranklinWH - Invalid Credentials %s", e)

    # TODO(richo) This should be memoized and shared among instances
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="franklinwh",
        update_method=_update_data,
        update_interval=update_interval,
        always_update=False
    )

    # Initial fetch (If we don't kick this off manually, we'll get unavailable
    # sensors until the first scheduled update).
    await coordinator.async_refresh()

    add_entities([
        SmartCircuitSwitch(prefix, unique_id, name, switches, client, coordinator),
        ])

# Is it chill to have a switch in here? We'll see!
class SmartCircuitSwitch(SwitchEntity):
    def __init__(self, prefix, unique_id, name, switches, client, coordinator):
        self._is_on = False
        self.switches = switches
        self._attr_name = "{} {}".format(prefix, name)
        self.client = client
        self.coordinator = coordinator
        if unique_id:
            self._attr_has_entity_name = True
            self._attr_unique_id = unique_id + "_" + name

    def update(self):
        state = self.coordinator.data
        if state is None:
            # I think this should never happen, since it wouldn't be Available but here we are
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

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        switches = [None, None, None]
        for i in self.switches:
            switches[i] = True
        await self.client.set_smart_switch_state(switches)
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        switches = [None, None, None]
        for i in self.switches:
            switches[i] = False
        await self.client.set_smart_switch_state(switches)
        await self.coordinator.async_refresh()
