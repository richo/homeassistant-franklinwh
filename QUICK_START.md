# Quick Start Guide

Get your FranklinWH integration up and running in 5 minutes! ⚡

## Prerequisites

- ✅ Home Assistant 2023.8 or newer
- ✅ HACS installed (recommended) OR manual installation
- ✅ FranklinWH account credentials
- ✅ Gateway ID (Serial Number from FranklinWH app)

## Installation (Choose One)

### Option A: HACS (Easiest)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click **⋮** → **Custom repositories**
4. Add: `https://github.com/richo/homeassistant-franklinwh`
5. Category: **Integration**
6. Click **Add**
7. Find **FranklinWH** and click **Download**
8. Restart Home Assistant

### Option B: Manual

1. Download latest release from GitHub
2. Extract to `config/custom_components/franklin_wh/`
3. Restart Home Assistant

## Setup (2 Minutes)

### Step 1: Get Your Gateway ID
1. Open FranklinWH mobile app
2. Go to **More** → **Site Address**
3. Note the **SN** (Serial Number) - this is your Gateway ID
   - Example: `100xxxxxxxxxxxx`

### Step 2: Add Integration
1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **FranklinWH**
4. Enter your details:
   ```
   Email Address: your@email.com
   Password: ••••••••
   Gateway ID: 100xxxxxxxxxxxx
   ```
5. Click **Submit**

### Step 3: Verify Setup
1. You should see "FranklinWH XXXXXX" device added
2. Click on the device to view 21 entities:
   - 18 sensors
   - 3 switches
3. Check that sensors are updating with real data

## First Things to Try

### 1. View Battery Status
Go to **Overview** dashboard and add a card:
```yaml
type: entity
entity: sensor.franklinwh_XXXXXX_state_of_charge
name: Battery Level
```

### 2. View Energy Flow
Create a picture-elements card showing:
- Solar Production
- Battery Use
- Home Load
- Grid Use

### 3. Control a Switch
Add a switch card:
```yaml
type: entities
entities:
  - switch.franklinwh_XXXXXX_switch_1
  - switch.franklinwh_XXXXXX_switch_2
  - switch.franklinwh_XXXXXX_switch_3
```

### 4. Add to Energy Dashboard
1. Go to **Settings** → **Dashboards** → **Energy**
2. Add sources:
   - **Solar**: `sensor.franklinwh_XXXXXX_solar_energy`
   - **Battery Charge**: `sensor.franklinwh_XXXXXX_battery_charge`
   - **Battery Discharge**: `sensor.franklinwh_XXXXXX_battery_discharge`
   - **Grid Import**: `sensor.franklinwh_XXXXXX_grid_import`
   - **Grid Export**: `sensor.franklinwh_XXXXXX_grid_export`

## Quick Automation Examples

### 1. Low Battery Alert
```yaml
automation:
  - alias: "Low Battery Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.franklinwh_XXXXXX_state_of_charge
        below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Battery low! Only {{ states('sensor.franklinwh_XXXXXX_state_of_charge') }}% remaining"
```

### 2. Turn Off Non-Essential Load When Battery Low
```yaml
automation:
  - alias: "Conserve Battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.franklinwh_XXXXXX_state_of_charge
        below: 15
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.franklinwh_XXXXXX_switch_3
```

### 3. Notify When Exporting to Grid
```yaml
automation:
  - alias: "Export to Grid"
    trigger:
      - platform: numeric_state
        entity_id: sensor.franklinwh_XXXXXX_grid_use
        above: 0.1  # Exporting more than 100W
        for:
          minutes: 5
    action:
      - service: notify.persistent_notification
        data:
          message: "Exporting {{ states('sensor.franklinwh_XXXXXX_grid_use') }} kW to grid!"
```

## Troubleshooting

### Nothing appears after setup
- Check **Settings** → **System** → **Logs** for errors
- Verify credentials in FranklinWH app
- Try re-authenticating the integration

### Entities show "Unavailable"
- Check internet connection
- Verify FranklinWH cloud is online
- Wait 60 seconds for first update
- Reload the integration

### Wrong Gateway ID?
1. Go to **Settings** → **Devices & Services**
2. Find FranklinWH integration
3. Click **Delete**
4. Add integration again with correct ID

### Need Help?
1. Download diagnostics (Settings → Devices & Services → FranklinWH → device → Download Diagnostics)
2. Check existing [GitHub Issues](https://github.com/richo/homeassistant-franklinwh/issues)
3. Create new issue with diagnostics attached

## Next Steps

- ✅ Read the full [README](README.md) for all features
- ✅ Explore custom [services](README.md#-services)
- ✅ Join Home Assistant community discussions
- ✅ Star the repo on GitHub if you find it useful!

## Tips & Tricks

💡 **Entity IDs**: Replace `XXXXXX` with last 6 digits of your Gateway ID

💡 **Faster Updates**: Enable "Use Local API" in integration options (experimental)

💡 **Entity Customization**: You can customize entity names and icons in Settings → Entities

💡 **Debugging**: Download diagnostics file for detailed system state

---

**You're all set! Enjoy your FranklinWH integration! 🎉**

