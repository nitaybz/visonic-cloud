"""Visonic Cloud API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE

_LOGGER = logging.getLogger(__name__)

SESSION_EXPIRED_STATUS = 440


class VisonicAuthError(Exception):
    """Authentication error."""


class VisonicConnectionError(Exception):
    """Connection error."""


class VisonicCloudApi:
    """Async API client for Visonic Cloud."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        app_id: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._email = email
        self._password = password
        self._app_id = app_id
        self._user_token: str | None = None
        self._session_token: str | None = None
        self._panel_serial: str | None = None
        self._user_code: str | None = None

    @property
    def user_token(self) -> str | None:
        """Return current user token."""
        return self._user_token

    @property
    def session_token(self) -> str | None:
        """Return current session token."""
        return self._session_token

    def set_tokens(self, user_token: str, session_token: str) -> None:
        """Set tokens from stored config."""
        self._user_token = user_token
        self._session_token = session_token

    def set_panel_info(self, panel_serial: str, user_code: str) -> None:
        """Set panel info for session login."""
        self._panel_serial = panel_serial
        self._user_code = user_code

    def _auth_headers(self) -> dict[str, str]:
        """Return headers with user-token."""
        headers: dict[str, str] = {}
        if self._user_token:
            headers["user-token"] = self._user_token
        return headers

    def _session_headers(self) -> dict[str, str]:
        """Return headers with user-token and session-token."""
        headers = self._auth_headers()
        if self._session_token:
            headers["session-token"] = self._session_token
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        retry_on_expire: bool = True,
    ) -> Any:
        """Make an API request with automatic session refresh."""
        url = f"{API_BASE}/{endpoint}"
        try:
            async with self._session.request(
                method, url, headers=headers, json=json_data
            ) as resp:
                if resp.status == SESSION_EXPIRED_STATUS and retry_on_expire:
                    _LOGGER.debug("Session expired (440), re-authenticating")
                    await self._full_reauth()
                    # Update headers with new tokens
                    if headers and "session-token" in headers:
                        headers = self._session_headers()
                    elif headers and "user-token" in headers:
                        headers = self._auth_headers()
                    return await self._request(
                        method, endpoint, headers, json_data, retry_on_expire=False
                    )

                if resp.status == 401:
                    raise VisonicAuthError("Authentication failed")

                if resp.status != 200:
                    text = await resp.text()
                    _LOGGER.error(
                        "API error %s for %s: %s", resp.status, endpoint, text
                    )
                    raise VisonicConnectionError(
                        f"API error {resp.status}: {text}"
                    )

                return await resp.json()

        except aiohttp.ClientError as err:
            raise VisonicConnectionError(
                f"Connection error: {err}"
            ) from err

    async def _full_reauth(self) -> None:
        """Re-authenticate fully (user auth + panel login)."""
        await self.authenticate()
        if self._panel_serial and self._user_code:
            await self.panel_login(self._panel_serial, self._user_code)

    async def authenticate(self) -> dict[str, Any]:
        """Authenticate with email and password. Returns user info with user_token."""
        try:
            async with self._session.post(
                f"{API_BASE}/auth",
                json={
                    "email": self._email,
                    "password": self._password,
                    "app_id": self._app_id,
                },
            ) as resp:
                if resp.status == 401:
                    raise VisonicAuthError("Invalid email or password")
                if resp.status != 200:
                    text = await resp.text()
                    raise VisonicConnectionError(
                        f"Auth failed with status {resp.status}: {text}"
                    )
                data = await resp.json()
                self._user_token = data["user_token"]
                return data
        except aiohttp.ClientError as err:
            raise VisonicConnectionError(
                f"Connection error during auth: {err}"
            ) from err

    async def get_panels(self) -> list[dict[str, Any]]:
        """Get list of panels for the authenticated user."""
        return await self._request("GET", "panels", headers=self._auth_headers())

    async def panel_login(
        self, panel_serial: str, user_code: str
    ) -> dict[str, Any]:
        """Login to a specific panel. Returns session info with session_token."""
        self._panel_serial = panel_serial
        self._user_code = user_code
        data = await self._request(
            "POST",
            "panel/login",
            headers=self._auth_headers(),
            json_data={
                "user_code": user_code,
                "app_id": self._app_id,
                "user_token": self._user_token,
                "panel_serial": panel_serial,
            },
            retry_on_expire=False,
        )
        self._session_token = data["session_token"]
        return data

    async def get_status(self) -> dict[str, Any]:
        """Get panel status."""
        return await self._request(
            "GET", "status", headers=self._session_headers()
        )

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get list of devices."""
        return await self._request(
            "GET", "devices", headers=self._session_headers()
        )

    async def get_alarms(self) -> list[dict[str, Any]]:
        """Get active alarms."""
        return await self._request(
            "GET", "alarms", headers=self._session_headers()
        )

    async def get_troubles(self) -> list[dict[str, Any]]:
        """Get active troubles."""
        return await self._request(
            "GET", "troubles", headers=self._session_headers()
        )

    async def get_events(self) -> list[dict[str, Any]]:
        """Get event log."""
        return await self._request(
            "GET", "events", headers=self._session_headers()
        )

    async def get_panel_info(self) -> dict[str, Any]:
        """Get panel information."""
        return await self._request(
            "GET", "panel_info", headers=self._session_headers()
        )

    async def arm_away(self, partition: int = -1) -> dict[str, Any]:
        """Arm the panel in away mode."""
        return await self._request(
            "POST",
            "set_state",
            headers=self._session_headers(),
            json_data={"state": "AWAY", "partition": partition},
        )

    async def arm_home(self, partition: int = -1) -> dict[str, Any]:
        """Arm the panel in home mode."""
        return await self._request(
            "POST",
            "set_state",
            headers=self._session_headers(),
            json_data={"state": "HOME", "partition": partition},
        )

    async def disarm(self, partition: int = -1) -> dict[str, Any]:
        """Disarm the panel."""
        return await self._request(
            "POST",
            "set_state",
            headers=self._session_headers(),
            json_data={"state": "DISARM", "partition": partition},
        )
