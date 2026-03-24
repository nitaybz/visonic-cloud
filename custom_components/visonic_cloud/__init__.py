"""The Visonic Cloud integration."""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VisonicCloudApi
from .const import (
    CONF_APP_ID,
    CONF_PANEL_SERIAL,
    CONF_SESSION_TOKEN,
    CONF_USER_CODE,
    CONF_USER_TOKEN,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import VisonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

type VisonicConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Visonic Cloud from a config entry."""
    session = async_get_clientsession(hass)

    api = VisonicCloudApi(
        session=session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        app_id=entry.data[CONF_APP_ID],
    )

    panel_serial = entry.data[CONF_PANEL_SERIAL]
    user_code = entry.data[CONF_USER_CODE]

    # Set panel info for auto-reauth
    api.set_panel_info(panel_serial, user_code)

    # Authenticate and login to panel
    await api.authenticate()
    await api.panel_login(panel_serial, user_code)

    coordinator = VisonicDataUpdateCoordinator(hass, api, panel_serial)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
