# FranklinWH Home Assistant Integration

This is a modern custom integration for [Home Assistant](https://www.home-assistant.io/) that provides comprehensive monitoring and control for FranklinWH home energy storage systems.

⚠️ **This project is unofficial and not affiliated with FranklinWH.**

## 📝 About This Fork

This fork adds **working operation mode control** to the excellent integration created by Joshua Seidel ([@JoshuaSeidel](https://github.com/JoshuaSeidel)).

**Credits:**
- **Complete rewrite**: Joshua Seidel ([@JoshuaSeidel](https://github.com/JoshuaSeidel)) with Anthropic Claude Sonnet 4.5
- **set_mode service implementation**: Based on [@j4m3z0r](https://github.com/j4m3z0r)'s working fork
- **Original integration**: [@richo](https://github.com/richo)
- **Python library**: [franklinwh-python](https://github.com/richo/franklinwh-python) by [@richo](https://github.com/richo)

## ✨ Features

### Monitoring
- 📊 Live battery status (State of Charge, charging/discharging power)
- ☀️ Solar production and energy generation tracking
- 🔌 Grid import/export monitoring with totals
- ⚡ Generator production and energy insights
- 🏠 Home load power monitoring
- 🔀 Smart circuit switch monitoring (Switches 1-3)
- 🚗 V2L (Vehicle-to-Load) data support

### Control
- 🎛️ **Individual smart circuit switch control**
- ⚙️ **Operation mode selection** (Time of Use, Self Consumption, Emergency Backup)
- 🔋 **Battery reserve setting** (integrated with mode selection)

### Integration Features
- 🎨 Config Flow: Easy setup through the Home Assistant UI
- 🔄 DataUpdateCoordinator: Efficient polling with minimal API calls
- 📱 Device Registry: All entities grouped under one device
- 🔍 Diagnostics: Built-in debugging support
- 🌐 Local API Support: Experimental local communication (when available)

## 🚀 Installation

### Via HACS (Recommended)

1. In Home Assistant, go to **HACS → Integrations**
2. Click the menu (⋮) → **Custom repositories**
3. Add this repository URL: `https://github.com/nrp929/homeassistant-franklinwh`
4. Choose category **Integration** and click **Add**
5. Search for **FranklinWH** in HACS and click **Download**
6. **Restart Home Assistant**

### Manual Installation

1. Download this repository as a ZIP file
2. Extract the contents to your Home Assistant `custom_components/franklin_wh/` directory
3. Restart Home Assistant

## ⚙️ Configuration

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for **FranklinWH**
4. Enter your credentials:
   - **Email Address**: Your FranklinWH account email
   - **Password**: Your FranklinWH account password
   - **Gateway ID**: Find this in the FranklinWH app under **More → Site Address → SN**
   - **Use Local API** (optional): Enable for experimental local communication
   - **Local Host** (optional): IP address of your FranklinWH gateway
5. Click **Submit** and your devices will be added automatically!

## 📊 Available Entities

### Sensors

| Entity | Description | Unit |
|--------|-------------|------|
| State of Charge | Battery state of charge | % |
| Battery Use | Battery charging/discharging rate (negative = charging) | kW |
| Battery Charge | Total energy charged to battery | kWh |
| Battery Discharge | Total energy discharged from battery | kWh |
| Battery Charge from Grid | Energy charged to battery from grid (calculated) | kWh |
| Home Load | Instantaneous home power consumption | kW |
| Grid Use | Net grid power (negative = importing, positive = exporting) | kW |
| Grid Import | Total energy imported from grid | kWh |
| Grid Export | Total energy exported to grid | kWh |
| Solar Production | Instantaneous solar power generation | kW |
| Solar Energy | Total solar energy produced | kWh |
| Generator Use | Generator power output (live) | kW |
| Generator Energy | Total generator energy produced | kWh |
| Switch 1 Load | Power draw on Switch 1 | W |
| Switch 1 Lifetime Use | Total energy used by Switch 1 | kWh |
| Switch 2 Load | Power draw on Switch 2 | W |
| Switch 2 Lifetime Use | Total energy used by Switch 2 | kWh |
| V2L Use | Power via Vehicle-to-Load | W |
| V2L Import | Total energy drawn from V2L | kWh |
| V2L Export | Total energy delivered to V2L | kWh |

### Switches

| Entity | Description |
|--------|-------------|
| Switch 1 | Control smart circuit 1 |
| Switch 2 | Control smart circuit 2 |
| Switch 3 | Control smart circuit 3 |

## 🛠️ Services

### `franklin_wh.set_mode`

Set the operation mode and battery reserve level of your FranklinWH system.

**Parameters:**
- `entity_id` (required): Any entity from your FranklinWH device
- `mode` (required): Operation mode
  - `"Time of Use"` - Optimizes battery usage based on time-of-use electricity rates
  - `"Self Consumption"` - Maximizes use of self-generated solar energy
  - `"Emergency Backup"` - Preserves battery charge for backup power during outages
- `soc` (optional): Minimum battery reserve level (0-100%). If not provided, current reserve level is preserved.

**Example Service Call:**

```yaml
service: franklin_wh.set_mode
data:
  entity_id: sensor.franklinwh_state_of_charge
  mode: "Time of Use"
  soc: 20
```

**Example Automations:**

```yaml
# Switch to self-consumption during the day
automation:
  - alias: "FranklinWH Day Mode"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: franklin_wh.set_mode
        data:
          entity_id: sensor.franklinwh_state_of_charge
          mode: "Self Consumption"
          soc: 20

  # Switch to emergency backup for severe weather
  - alias: "FranklinWH Emergency Mode for Severe Weather"
    trigger:
      - platform: state
        entity_id: weather.home
        attribute: warning
    condition:
      - condition: template
        value_template: "{{ 'severe' in trigger.to_state.attributes.warning }}"
    action:
      - service: franklin_wh.set_mode
        data:
          entity_id: sensor.franklinwh_state_of_charge
          mode: "Emergency Backup"
          soc: 100
```

## 📈 Energy Dashboard Integration

All energy sensors are compatible with Home Assistant's Energy Dashboard:

1. Go to **Settings → Dashboards → Energy**
2. Configure your energy sources:
   - **Solar Production**: Use "Solar Energy" sensor
   - **Battery**: Use "Battery Charge" and "Battery Discharge" sensors
   - **Battery from Grid**: Use "Battery Charge from Grid" sensor (calculated)
   - **Grid**: Use "Grid Import" and "Grid Export" sensors

## 🔧 Troubleshooting

### No entities appear after setup
- Check **Settings → System → Logs** for errors containing `franklin_wh`
- Verify your credentials are correct
- Confirm your Gateway ID is correct (found in FranklinWH app)
- Ensure FranklinWH cloud services are online

### Authentication failures
- Try re-authenticating:
  1. Go to **Settings → Devices & Services**
  2. Find your FranklinWH integration
  3. Click **Configure → Re-authenticate**
- Verify your password is correct
- Check your internet connection
- Verify the FranklinWH cloud service is accessible

### Connection issues
- Check the integration logs for API errors
- Try reloading the integration
- If you see "Device response timed out":
  - Verify gateway is online in the FranklinWH mobile app
  - Check Gateway ID matches the SN in app (More → Site Address → SN)
  - FranklinWH cloud service may be temporarily down
  - If using local API, try switching back to cloud polling
  - Gateway may be rebooting or updating

### set_mode service doesn't work
- Ensure you're using franklinwh library version 0.6.0 or newer
- Check logs for specific error messages
- Verify the mode name is spelled correctly (case-sensitive)

### Diagnostics

To get detailed diagnostic information:
1. Go to **Settings → Devices & Services**
2. Find your FranklinWH integration
3. Click the device, then click **Download Diagnostics**
4. Attach the diagnostics file when reporting issues

## 🌐 Local API Support (Experimental)

This integration includes experimental support for local API communication.

To enable local API:
- Enable "Use Local API" during setup
- Enter your gateway's local IP address
- The integration will attempt local communication with faster polling (10 seconds vs 60 seconds)

**Note**: Local API support depends on the underlying `franklinwh` Python library and gateway firmware version. Most users should use cloud polling (default).

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test your changes thoroughly
4. Submit a pull request

When reporting issues, please:
- Download diagnostics from your integration
- Include Home Assistant and integration versions
- Provide relevant log entries
- Describe steps to reproduce

## 📋 Changelog

### Version 1.0.9
- ✨ **NEW**: Working `set_mode` service for operation mode control
- ✨ **NEW**: Support for battery reserve percentage setting
- ⬆️ **UPDATED**: Requires franklinwh library 0.6.0+ (includes Mode class)
- 🧹 **REMOVED**: Deprecated placeholder services
- 📝 **IMPROVED**: Updated documentation with service examples
- 🙏 **CREDITS**: set_mode implementation based on [@j4m3z0r](https://github.com/j4m3z0r)'s work

### Version 1.0.8 (upstream)
- 🐛 CRITICAL FIX: Removed Grid Connection switch (requires unreleased library version)
- 🐛 FIXED: ImportError for AccessoryType and GridStatus classes
- 🐛 FIXED: Integration now loads successfully with franklinwh 0.4.1
- ℹ️ NOTE: Smart circuit switches (1-3) still work correctly

[See full changelog in original repository](https://github.com/JoshuaSeidel/homeassistant-franklinwh)

## 📜 License

This project is dual-licensed under:
- MIT License
- Apache License 2.0

You may choose either license when using or contributing to this project.

## 🙏 Acknowledgments

- **Original Integration**: [@richo](https://github.com/richo) for the initial implementation
- **Python Library**: [franklinwh-python](https://github.com/richo/franklinwh-python) by [@richo](https://github.com/richo)
- **Complete Rewrite**: Joshua Seidel ([@JoshuaSeidel](https://github.com/JoshuaSeidel)) with Anthropic Claude Sonnet 4.5
- **set_mode Implementation**: [@j4m3z0r](https://github.com/j4m3z0r) for the working mode control implementation
- **Community**: Thanks to the Home Assistant community and all contributors

## ⚠️ Disclaimer

This integration is not affiliated with, endorsed by, or supported by FranklinWH. Use at your own risk. The developers are not responsible for any damage to your system or equipment.

---

**Enjoy your FranklinWH integration!** 🎉

For support, please open an issue on [GitHub](https://github.com/nrp929/homeassistant-franklinwh/issues).
