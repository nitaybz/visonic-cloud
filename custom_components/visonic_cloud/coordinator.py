"""DataUpdateCoordinator for Visonic Cloud."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import VisonicAuthError, VisonicCloudApi, VisonicConnectionError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class VisonicDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching Visonic data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: VisonicCloudApi,
        panel_serial: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api
        self.panel_serial = panel_serial

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API."""
        try:
            status = await self.api.get_status()
            devices = await self.api.get_devices()
            alarms = await self.api.get_alarms()

            return {
                "status": status,
                "devices": devices,
                "alarms": alarms,
            }

        except VisonicAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except VisonicConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
