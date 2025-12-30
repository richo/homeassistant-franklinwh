"""Utilities for FranklinWH integration."""

from franklinwh.client import Client, TokenFetcher
import httpx

from homeassistant.core import HomeAssistant


async def get_client(
    hass: HomeAssistant,
    username: str,
    password: str,
    gateway_id: str,
):
    """Create and return a franklinwh TokenFetcher and Client."""
    session = await hass.async_add_executor_job(lambda: httpx.AsyncClient(http2=True))
    token_fetcher = TokenFetcher(username, password, session=session)
    client = Client(token_fetcher, gateway_id, session=session)
    return (token_fetcher, client)
