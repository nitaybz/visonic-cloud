"""Config flow for Visonic Cloud integration."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VisonicAuthError, VisonicCloudApi, VisonicConnectionError
from .const import (
    CONF_APP_ID,
    CONF_PANEL_ALIAS,
    CONF_PANEL_SERIAL,
    CONF_USER_CODE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class VisonicCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Visonic Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._email: str = ""
        self._password: str = ""
        self._app_id: str = ""
        self._user_token: str = ""
        self._panels: list[dict[str, Any]] = []
        self._panel_serial: str = ""
        self._panel_alias: str = ""
        self._api: VisonicCloudApi | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - email and password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            self._app_id = str(uuid.uuid4())

            session = async_get_clientsession(self.hass)
            self._api = VisonicCloudApi(
                session=session,
                email=self._email,
                password=self._password,
                app_id=self._app_id,
            )

            try:
                await self._api.authenticate()
                self._panels = await self._api.get_panels()
            except VisonicAuthError:
                errors["base"] = "invalid_auth"
            except VisonicConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during authentication")
                errors["base"] = "unknown"

            if not errors:
                if not self._panels:
                    errors["base"] = "no_panels"
                elif len(self._panels) == 1:
                    # Auto-select the only panel
                    panel = self._panels[0]
                    self._panel_serial = panel["panel_serial"]
                    self._panel_alias = panel.get("alias", "")
                    return await self.async_step_panel_code()
                else:
                    return await self.async_step_select_panel()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_panel(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle panel selection when multiple panels exist."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input[CONF_PANEL_SERIAL]
            for panel in self._panels:
                if panel["panel_serial"] == selected:
                    self._panel_serial = panel["panel_serial"]
                    self._panel_alias = panel.get("alias", "")
                    break
            return await self.async_step_panel_code()

        panel_options = {
            panel["panel_serial"]: (
                f"{panel.get('alias', panel['panel_serial'])} ({panel.get('panel_model', 'Unknown')})"
            )
            for panel in self._panels
        }

        return self.async_show_form(
            step_id="select_panel",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PANEL_SERIAL): vol.In(panel_options),
                }
            ),
            errors=errors,
        )

    async def async_step_panel_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle panel code entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_code = user_input[CONF_USER_CODE]

            try:
                await self._api.panel_login(self._panel_serial, user_code)
            except VisonicAuthError:
                errors["base"] = "invalid_code"
            except VisonicConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during panel login")
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(self._panel_serial)
                self._abort_if_unique_id_configured()

                title = self._panel_alias or f"Visonic {self._panel_serial}"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_EMAIL: self._email,
                        CONF_PASSWORD: self._password,
                        CONF_APP_ID: self._app_id,
                        CONF_PANEL_SERIAL: self._panel_serial,
                        CONF_PANEL_ALIAS: self._panel_alias,
                        CONF_USER_CODE: user_code,
                    },
                )

        return self.async_show_form(
            step_id="panel_code",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USER_CODE): str,
                }
            ),
            errors=errors,
        )
