"""Config flow for FranklinWH integration."""

from __future__ import annotations

import logging
from typing import Any

import franklinwh
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import CONF_GATEWAY_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    gateway_id = data[CONF_GATEWAY_ID]

    try:
        token_fetcher = franklinwh.TokenFetcher(username, password)
        client = franklinwh.Client(token_fetcher, gateway_id)

        # Try to fetch data to validate credentials and gateway
        stats = await client.get_stats()

        if stats is None:
            raise CannotConnect("Unable to fetch data from FranklinWH")

        # Return info that you want to store in the config entry.
        return {
            "title": f"FranklinWH {gateway_id[-6:]}",
            "gateway_id": gateway_id,
        }
    except Exception as err:
        _LOGGER.exception("Unexpected exception: %s", err)
        error_str = str(err).lower()

        # Check for specific error types
        if "timeout" in error_str or "timed out" in error_str:
            _LOGGER.error("Device timeout - gateway may be offline or unreachable")
            raise CannotConnect(
                "Gateway device timed out. Please verify:\n"
                "1. Gateway is powered on and connected to network\n"
                "2. Gateway ID is correct\n"
                "3. FranklinWH cloud services are online"
            ) from err

        if "auth" in error_str or "token" in error_str or "401" in error_str:
            raise InvalidAuth from err

        if "gateway" in error_str or "device" in error_str:
            raise InvalidGateway from err

        raise CannotConnect from err


class FranklinWHConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FranklinWH."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_GATEWAY_ID])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidGateway:
                errors["base"] = "invalid_gateway"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        # Build the data schema
        # Note: Local API fields are shown but not functional yet
        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_GATEWAY_ID): cv.string,
                # Local API not functional yet - fields shown but ignored
                # vol.Optional(CONF_USE_LOCAL_API, default=False): cv.boolean,
                # vol.Optional(CONF_LOCAL_HOST): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth when credentials are invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Get the existing entry
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if entry is None:
                return self.async_abort(reason="reauth_failed")

            # Combine existing data with new credentials
            data = {**entry.data, **user_input}

            try:
                await validate_input(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> FranklinWHOptionsFlow:
        """Get the options flow for this handler."""
        return FranklinWHOptionsFlow(config_entry)


class FranklinWHOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for FranklinWH."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        scan_interval = self.config_entry.options.get(
            "scan_interval",
            DEFAULT_SCAN_INTERVAL,
        )

        data_schema = vol.Schema(
            {
                vol.Optional("scan_interval", default=scan_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=30, max=3600)
                ),
                # Local API options disabled - not functional yet
                # vol.Optional(CONF_USE_LOCAL_API, default=False): cv.boolean,
                # vol.Optional(CONF_LOCAL_HOST, default=""): cv.string,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidGateway(HomeAssistantError):
    """Error to indicate the gateway ID is invalid."""
