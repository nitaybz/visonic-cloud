# Visonic Cloud Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant custom integration for **Visonic PowerMaster** alarm systems via the Visonic Cloud API.

## Features

- **Alarm Control Panel** - Arm (Home/Away) and Disarm your Visonic system
- **Binary Sensors** - Door/window contacts and motion detectors with real-time status
- **Temperature & Brightness Sensors** - Environmental data from PIR sensors that support it
- **Multi-panel support** - Configure multiple panels from a single Visonic account
- **Hebrew & English** - Full translation support

## Supported Devices

| Device | Entity Type |
|--------|-------------|
| Door/Window contacts (MC303) | Binary Sensor (door) |
| Motion detectors (PIR) | Binary Sensor (motion) |
| Curtain detectors | Binary Sensor (motion) |
| PIR with temperature | Sensor (temperature, °C) |
| PIR with brightness | Sensor (illuminance, lx) |
| Panel partitions | Alarm Control Panel |

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu in the top right corner
3. Select **Custom repositories**
4. Add `https://github.com/nitaybz/visonic-cloud` with category **Integration**
5. Click **Install**
6. Restart Home Assistant

### Manual

1. Copy the `custom_components/visonic_cloud` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Visonic Cloud**
3. Enter your Visonic Cloud email and password
4. If you have multiple panels, select the one to configure
5. Enter the panel user code (4-digit PIN)

## Requirements

- A Visonic PowerMaster alarm system with cloud connectivity (PowerLink3 or similar)
- A Visonic Cloud account (the same one used in the Visonic Go / PowerManage app)
- The panel user code (master or user PIN)

## Notes

- The integration polls the Visonic Cloud API every 30 seconds
- Arm/Disarm commands are sent through the cloud and may take a few seconds to reflect
- The user code is stored securely in the Home Assistant config entry
- Each panel is registered as a separate device in the HA device registry
- Zone devices (sensors, contacts) appear as sub-devices under the panel
