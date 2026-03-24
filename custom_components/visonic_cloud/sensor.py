"""Sensor platform for Visonic Cloud."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature

LIGHT_LUX = "lx"
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PANEL_ALIAS,
    CONF_PANEL_SERIAL,
    DEVICE_TYPE_ZONE,
    DOMAIN,
)
from .coordinator import VisonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: VisonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    panel_serial = entry.data[CONF_PANEL_SERIAL]
    panel_alias = entry.data.get(CONF_PANEL_ALIAS, "")

    devices = coordinator.data.get("devices", [])
    entities: list[SensorEntity] = []

    for device in devices:
        if device.get("device_type") != DEVICE_TYPE_ZONE:
            continue

        traits = device.get("traits", {})
        meteo_info = traits.get("meteo_info", {})
        location = traits.get("location", {})
        device_name = location.get("name", device.get("name", f"Zone {device.get('device_number', 0)}"))
        device_id = device["id"]

        # Temperature sensor
        if "temperature" in meteo_info:
            entities.append(
                VisonicTemperatureSensor(
                    coordinator=coordinator,
                    panel_serial=panel_serial,
                    device_id=device_id,
                    device_name=device_name,
                    subtype=device.get("subtype", ""),
                )
            )

        # Brightness sensor
        if "brightness" in meteo_info:
            entities.append(
                VisonicBrightnessSensor(
                    coordinator=coordinator,
                    panel_serial=panel_serial,
                    device_id=device_id,
                    device_name=device_name,
                    subtype=device.get("subtype", ""),
                )
            )

    # Last event sensor (one per panel)
    entities.append(
        VisonicLastEventSensor(
            coordinator=coordinator,
            panel_serial=panel_serial,
            panel_alias=panel_alias,
        )
    )

    async_add_entities(entities)


class VisonicTemperatureSensor(
    CoordinatorEntity[VisonicDataUpdateCoordinator], SensorEntity
):
    """Temperature sensor from a Visonic PIR device."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: VisonicDataUpdateCoordinator,
        panel_serial: str,
        device_id: int,
        device_name: str,
        subtype: str,
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator)
        self._panel_serial = panel_serial
        self._device_id = device_id

        self._attr_unique_id = f"{panel_serial}_{device_id}_temperature"
        self._attr_name = "Temperature"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{panel_serial}_{device_id}")},
            name=device_name,
            manufacturer="Visonic",
            model=subtype or None,
            via_device=(DOMAIN, panel_serial),
        )

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get current device data from coordinator."""
        devices = self.coordinator.data.get("devices", [])
        for device in devices:
            if device["id"] == self._device_id:
                return device
        return None

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        device = self._get_device_data()
        if device is None:
            return None

        traits = device.get("traits", {})
        meteo = traits.get("meteo_info", {})
        temp = meteo.get("temperature", {})
        value = temp.get("value")

        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        return None


class VisonicBrightnessSensor(
    CoordinatorEntity[VisonicDataUpdateCoordinator], SensorEntity
):
    """Brightness sensor from a Visonic PIR device."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = LIGHT_LUX

    def __init__(
        self,
        coordinator: VisonicDataUpdateCoordinator,
        panel_serial: str,
        device_id: int,
        device_name: str,
        subtype: str,
    ) -> None:
        """Initialize the brightness sensor."""
        super().__init__(coordinator)
        self._panel_serial = panel_serial
        self._device_id = device_id

        self._attr_unique_id = f"{panel_serial}_{device_id}_brightness"
        self._attr_name = "Brightness"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{panel_serial}_{device_id}")},
            name=device_name,
            manufacturer="Visonic",
            model=subtype or None,
            via_device=(DOMAIN, panel_serial),
        )

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get current device data from coordinator."""
        devices = self.coordinator.data.get("devices", [])
        for device in devices:
            if device["id"] == self._device_id:
                return device
        return None

    @property
    def native_value(self) -> float | None:
        """Return the brightness value."""
        device = self._get_device_data()
        if device is None:
            return None

        traits = device.get("traits", {})
        meteo = traits.get("meteo_info", {})
        brightness = meteo.get("brightness", {})
        value = brightness.get("value")

        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        return None


class VisonicLastEventSensor(
    CoordinatorEntity[VisonicDataUpdateCoordinator], SensorEntity
):
    """Sensor showing the last event from the panel."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:history"

    def __init__(
        self,
        coordinator: VisonicDataUpdateCoordinator,
        panel_serial: str,
        panel_alias: str,
    ) -> None:
        """Initialize the last event sensor."""
        super().__init__(coordinator)
        self._panel_serial = panel_serial

        self._attr_unique_id = f"{panel_serial}_last_event"
        self._attr_name = "Last event"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, panel_serial)},
            name=panel_alias or f"Visonic {panel_serial}",
            manufacturer="Visonic",
        )

    @property
    def native_value(self) -> str | None:
        """Return the last event description."""
        # Events are not fetched in the coordinator by default to save API calls.
        # We use alarms data as a proxy for the most recent event.
        alarms = self.coordinator.data.get("alarms", [])
        if alarms:
            last_alarm = alarms[-1]
            alarm_type = last_alarm.get("alarm_type", "")
            location = last_alarm.get("location", "")
            dt = last_alarm.get("datetime", "")
            return f"{alarm_type} - {location} ({dt})"

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes with alarm details."""
        alarms = self.coordinator.data.get("alarms", [])
        if not alarms:
            return {}

        last_alarm = alarms[-1]
        return {
            "alarm_type": last_alarm.get("alarm_type"),
            "device_type": last_alarm.get("device_type"),
            "zone": last_alarm.get("zone"),
            "zone_type": last_alarm.get("zone_type"),
            "datetime": last_alarm.get("datetime"),
            "location": last_alarm.get("location"),
        }
