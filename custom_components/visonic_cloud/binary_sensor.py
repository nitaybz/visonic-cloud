"""Binary sensor platform for Visonic Cloud."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PANEL_SERIAL,
    DEVICE_TYPE_ZONE,
    DOMAIN,
    SUBTYPE_CURTAIN,
    SUBTYPE_FLAT_PIR_SMART,
    SUBTYPE_MC303_VANISH,
)
from .coordinator import VisonicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SUBTYPE_DEVICE_CLASS_MAP = {
    SUBTYPE_MC303_VANISH: BinarySensorDeviceClass.DOOR,
    SUBTYPE_FLAT_PIR_SMART: BinarySensorDeviceClass.MOTION,
    SUBTYPE_CURTAIN: BinarySensorDeviceClass.MOTION,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: VisonicDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    panel_serial = entry.data[CONF_PANEL_SERIAL]

    devices = coordinator.data.get("devices", [])
    entities = []

    for device in devices:
        if device.get("device_type") != DEVICE_TYPE_ZONE:
            continue

        entities.append(
            VisonicZoneBinarySensor(
                coordinator=coordinator,
                panel_serial=panel_serial,
                device=device,
            )
        )

    async_add_entities(entities)


class VisonicZoneBinarySensor(
    CoordinatorEntity[VisonicDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Visonic zone as a binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VisonicDataUpdateCoordinator,
        panel_serial: str,
        device: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._panel_serial = panel_serial
        self._device_id = device["id"]
        self._device_number = device.get("device_number", 0)

        # Determine device class from subtype
        subtype = device.get("subtype", "")
        self._attr_device_class = SUBTYPE_DEVICE_CLASS_MAP.get(subtype)

        # Name from location trait
        traits = device.get("traits", {})
        location = traits.get("location", {})
        device_name = location.get("name", device.get("name", f"Zone {self._device_number}"))

        self._attr_unique_id = f"{panel_serial}_{self._device_id}"
        self._attr_name = device_name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{panel_serial}_{self._device_id}")},
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
    def is_on(self) -> bool | None:
        """Return true if the zone has an active alarm or warning."""
        device = self._get_device_data()
        if device is None:
            return None

        # Check device-level warnings (ignore in-memory)
        warnings = device.get("warnings", [])
        for warning in (warnings or []):
            if warning.get("type") != "ALARM_IN_MEMORY":
                return True

        # Check active alarms for this zone (ignore in-memory)
        alarms = self.coordinator.data.get("alarms", [])
        for alarm in alarms:
            if alarm.get("alarm_type") == "ALARM_IN_MEMORY":
                continue
            if alarm.get("zone") == self._device_number:
                return True

        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        device = self._get_device_data()
        if device is None:
            return {}

        attrs: dict[str, Any] = {
            "zone_number": device.get("device_number"),
            "zone_type": device.get("zone_type"),
        }

        # Add enrollment_id if present
        enrollment_id = device.get("enrollment_id")
        if enrollment_id:
            attrs["enrollment_id"] = enrollment_id

        return attrs
