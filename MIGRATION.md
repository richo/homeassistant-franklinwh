# Migration Guide: v0.4.1 → v1.0.0

This guide will help you migrate from the legacy YAML-based configuration to the modern Config Flow setup.

## What's Changed

### Major Changes
- ✅ **Config Flow**: Setup through UI instead of YAML
- ✅ **Device Registry**: All entities grouped under one device
- ✅ **DataUpdateCoordinator**: More efficient API polling
- ✅ **Diagnostics**: Built-in debugging support
- ✅ **Services**: New custom services for advanced control
- ✅ **Better Error Handling**: Automatic re-authentication flow

### Breaking Changes
- ⚠️ **Entity IDs may change**: Unique IDs are now properly formatted
- ⚠️ **Switch configuration**: Switches are now automatically created (no manual configuration needed)
- ⚠️ **YAML config deprecated**: Platform-based YAML configuration will be removed in v2.0.0

## Migration Steps

### Step 1: Backup Your Configuration

Before starting, backup:
1. Your `configuration.yaml` file
2. Any automations using FranklinWH entities
3. Your dashboard configurations

### Step 2: Note Your Entity IDs

Make a list of your current entity IDs and how they're used in:
- Automations
- Scripts
- Dashboard cards
- Utility meter entities

Example entities that may exist:
```
sensor.franklinwh_state_of_charge
sensor.franklinwh_battery_use
sensor.franklinwh_home_load
switch.fwh_switch1
```

### Step 3: Remove YAML Configuration

1. Open your `configuration.yaml` file
2. Remove the old FranklinWH configuration:

```yaml
# REMOVE THESE:
sensor:
  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: "100xxxxxxxxxxxx"

switch:
  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: "100xxxxxxxxxxxx"
    switches: [1, 2, 3]
    name: "FWH switch1"
```

3. Save the file
4. **Restart Home Assistant**

### Step 4: Add Integration via UI

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for **FranklinWH**
4. Enter your credentials:
   - Email Address
   - Password
   - Gateway ID (same as before)
5. Click **Submit**

### Step 5: Update Entity References

After setup, you'll have new entity IDs. They will follow this format:
```
sensor.franklinwh_<gateway_last_6_digits>_<sensor_name>
```

Example new entity IDs:
```
sensor.franklinwh_123456_state_of_charge
sensor.franklinwh_123456_battery_use
sensor.franklinwh_123456_home_load
switch.franklinwh_123456_switch_1
switch.franklinwh_123456_switch_2
switch.franklinwh_123456_switch_3
```

**Update these in:**
1. **Automations**: Edit each automation and update entity IDs
2. **Scripts**: Update entity references
3. **Dashboard Cards**: Update entity selections
4. **Utility Meters**: Reconfigure source entities

### Step 6: Verify Everything Works

1. Check **Settings → Devices & Services** → **FranklinWH**
2. Click on your device to see all entities
3. Verify all sensors are updating
4. Test switch controls
5. Check your automations and dashboards

### Step 7: Energy Dashboard (Optional)

If you're using the Energy Dashboard, reconfigure it:

1. Go to **Settings → Dashboards → Energy**
2. Update energy sources with new entity IDs:
   - Solar: `sensor.franklinwh_XXXXXX_solar_energy`
   - Battery Charge: `sensor.franklinwh_XXXXXX_battery_charge`
   - Battery Discharge: `sensor.franklinwh_XXXXXX_battery_discharge`
   - Grid Import: `sensor.franklinwh_XXXXXX_grid_import`
   - Grid Export: `sensor.franklinwh_XXXXXX_grid_export`

## Troubleshooting

### Old entities still showing
1. Go to **Settings → Devices & Services → Entities**
2. Search for `franklinwh`
3. Delete any old entities manually
4. Restart Home Assistant

### Entity IDs don't match
The new format includes the last 6 digits of your gateway ID. You can:
- Use entity ID customization to rename them
- Or update all references to use the new IDs

### Missing entities
1. Check **Settings → System → Logs** for errors
2. Download diagnostics from the integration
3. Try reloading the integration

### Switches not working
- All 3 switches are now created automatically
- Test each switch individually
- Check diagnostics if switches show as unavailable

## Entity Naming Quick Reference

| Old Entity (Example) | New Entity Format |
|---------------------|-------------------|
| `sensor.franklinwh_state_of_charge` | `sensor.franklinwh_XXXXXX_state_of_charge` |
| `sensor.franklinwh_battery_use` | `sensor.franklinwh_XXXXXX_battery_use` |
| `sensor.franklinwh_home_load` | `sensor.franklinwh_XXXXXX_home_load` |
| `switch.fwh_switch1` | `switch.franklinwh_XXXXXX_switch_1` |

*Replace `XXXXXX` with the last 6 digits of your gateway ID*

## New Features to Try

### Diagnostics
Download diagnostics to help troubleshoot issues:
1. Go to your FranklinWH device
2. Click **Download Diagnostics**

### Services
Try the new custom services (when API support is available):
```yaml
service: franklin_wh.set_operation_mode
data:
  mode: self_use
```

### Local API (Experimental)
Enable local API in integration options for faster polling:
1. Go to integration settings
2. Enable "Use Local API"
3. Enter your gateway's local IP address

## Rollback Instructions

If you need to rollback to the old version:

1. Remove the integration from UI:
   - Settings → Devices & Services
   - Find FranklinWH
   - Click menu → Delete

2. Downgrade to v0.4.1:
   - In HACS, find FranklinWH
   - Click menu → Redownload
   - Select version 0.4.1

3. Restore your `configuration.yaml` from backup

4. Restart Home Assistant

## Need Help?

- Check the [README](README.md) for detailed documentation
- Review [GitHub Issues](https://github.com/richo/homeassistant-franklinwh/issues)
- Download and share diagnostics when reporting problems

---

**Happy Migrating! 🚀**

