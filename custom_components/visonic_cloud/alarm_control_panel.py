"""Alarm control panel platform for Visonic Cloud."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PANEL_ALIAS,
    CONF_PANEL_SERIAL,
    DOMAIN,
    PARTITION_STATE_AWAY,
    PARTITION_STATE_DISARM,
    PARTITION_STATE_EXIT,
    PARTITION_STATE_HOME,
)
from .coordinator import VisonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PARTITION_STATE_MAP = {
    PARTITION_STATE_DISARM: AlarmControlPanelState.DISARMED,
    PARTITION_STATE_AWAY: AlarmControlPanelState.ARMED_AWAY,
    PARTITION_STATE_HOME: AlarmControlPanelState.ARMED_HOME,
    PARTITION_STATE_EXIT: AlarmControlPanelState.ARMING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up alarm control panel entities."""
    coordinator: VisonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    panel_serial = entry.data[CONF_PANEL_SERIAL]
    panel_alias = entry.data.get(CONF_PANEL_ALIAS, "")

    status = coordinator.data.get("status", {})
    partitions = status.get("partitions", [])

    entities = []
    for partition in partitions:
        entities.append(
            VisonicAlarmControlPanel(
                coordinator=coordinator,
                panel_serial=panel_serial,
                panel_alias=panel_alias,
                partition_id=partition["id"],
            )
        )

    # If no partitions found, create a default one
    if not entities:
        entities.append(
            VisonicAlarmControlPanel(
                coordinator=coordinator,
                panel_serial=panel_serial,
                panel_alias=panel_alias,
                partition_id=-1,
            )
        )

    async_add_entities(entities)


class VisonicAlarmControlPanel(
    CoordinatorEntity[VisonicDataUpdateCoordinator], AlarmControlPanelEntity
):
    """Representation of a Visonic alarm control panel partition."""

    _attr_has_entity_name = True
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )

    def __init__(
        self,
        coordinator: VisonicDataUpdateCoordinator,
        panel_serial: str,
        panel_alias: str,
        partition_id: int,
    ) -> None:
        """Initialize the alarm control panel."""
        super().__init__(coordinator)
        self._panel_serial = panel_serial
        self._panel_alias = panel_alias
        self._partition_id = partition_id

        self._attr_unique_id = f"{panel_serial}_partition_{partition_id}"

        if partition_id == -1:
            self._attr_name = None  # Use device name
        else:
            self._attr_name = f"Partition {partition_id}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, panel_serial)},
            name=panel_alias or f"Visonic {panel_serial}",
            manufacturer="Visonic",
            model=self._get_panel_model(),
            serial_number=panel_serial,
        )

    def _get_panel_model(self) -> str | None:
        """Get panel model from devices list."""
        devices = self.coordinator.data.get("devices", [])
        for device in devices:
            if device.get("device_type") == "CONTROL_PANEL":
                return device.get("subtype")
        return None

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the alarm."""
        # Check for active alarms (ignore ALARM_IN_MEMORY which are historical)
        alarms = self.coordinator.data.get("alarms", [])
        for alarm in alarms:
            if alarm.get("alarm_type") == "ALARM_IN_MEMORY":
                continue
            alarm_partitions = alarm.get("partitions", [])
            if self._partition_id == -1 or self._partition_id in alarm_partitions:
                return AlarmControlPanelState.TRIGGERED

        # Map partition state
        status = self.coordinator.data.get("status", {})
        partitions = status.get("partitions", [])

        for partition in partitions:
            if partition["id"] == self._partition_id or self._partition_id == -1:
                state = partition.get("state", "")
                return PARTITION_STATE_MAP.get(state, AlarmControlPanelState.DISARMED)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        status = self.coordinator.data.get("status", {})
        attrs: dict[str, Any] = {
            "panel_serial": self._panel_serial,
        }

        # Panel model
        model = self._get_panel_model()
        if model:
            attrs["panel_model"] = model

        # Connection status
        attrs["connected"] = status.get("connected", False)
        connected_status = status.get("connected_status", {})
        bba = connected_status.get("bba", {})
        attrs["bba_connected"] = bba.get("is_connected", False)

        # Partition ready state
        partitions = status.get("partitions", [])
        for partition in partitions:
            if partition["id"] == self._partition_id or self._partition_id == -1:
                attrs["ready"] = partition.get("ready", False)
                break

        return attrs

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self.coordinator.api.disarm(self._partition_id)
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self.coordinator.api.arm_home(self._partition_id)
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self.coordinator.api.arm_away(self._partition_id)
        await self.coordinator.async_request_refresh()
