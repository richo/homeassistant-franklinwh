# FranklinWH Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-blue.svg?style=for-the-badge)](https://github.com/hacs/integration)

This is a custom integration for [Home Assistant](https://www.home-assistant.io/) that provides monitoring for FranklinWH home energy storage systems.

> ⚠️ This project is unofficial and not affiliated with FranklinWH.

---

## Features

- Live battery status (SoC, charging/discharging)
- Solar production and energy generation
- Grid import/export monitoring
- Generator and home load insights
- Switch load and usage tracking
- Support for V2L (Vehicle-to-Load) data

---

## Installation

### Via HACS (Recommended)

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the menu (⋮) → **Custom repositories**.
3. Add this repository URL: https://github.com/richo/homeassistant-franklinwh.git
4. Choose category **Integration** and click **Add**.
5. Install the **FranklinWH** integration from the list.
6. Restart Home Assistant.

### Manual Installation (Advanced)

1. Download this repository as a ZIP.
2. Extract it to your Home Assistant `custom_components/franklin_wh/` directory.
3. Restart Home Assistant.

---

## Configuration

This integration currently requires **manual YAML configuration** in your `configuration.yaml` file.

> 💡 For security, store your password in `secrets.yaml` instead of writing it directly in your config.
>
> You can find your Gateway ID / Serial Number in the FranklinWH mobile app under:
> Settings → Device Info → SN


### Configuration Example

```yaml
sensor:
- platform: franklin_wh
 username: "email@domain.com"
 password: !secret franklinwh_password
 id: "100xxxxxxxxxxxx"

### Switch Configuration Example

switch:
  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: "100xxxxxxxxxxxx"
    switches: [3]
    name: "FWH switch1"

  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: "100xxxxxxxxxxxx"
    switches: [1, 2]
    name: "FWH switch2"

## Available Entities

| Entity Name                          | Description                               | Unit      |
|-------------------------------------|-------------------------------------------|-----------|
| FranklinWH State of Charge          | Battery state of charge                   | %         |
| FranklinWH Battery Use              | Battery charging/discharging rate         | kW        |
| FranklinWH Battery Charge           | Total energy charged to battery           | kWh       |
| FranklinWH Battery Discharge        | Total energy discharged from battery      | kWh       |
| FranklinWH Home Load                | Instantaneous home power use              | kW        |
| FranklinWH Grid Use                 | Net grid power usage                      | kW        |
| FranklinWH Grid Import              | Total energy imported from grid           | kWh       |
| FranklinWH Grid Export              | Total energy exported to grid             | kWh       |
| FranklinWH Solar Production         | Instantaneous solar power                 | kW        |
| FranklinWH Solar Energy             | Total solar energy produced               | kWh       |
| FranklinWH Generator Use            | Generator power output (live)             | kW        |
| FranklinWH Generator Energy         | Total generator energy                    | kWh       |
| FranklinWH Switch 1 Load            | Power draw on Switch 1                    | W         |
| FranklinWH Switch 1 Lifetime Use    | Total energy used by Switch 1             | Wh        |
| FranklinWH Switch 2 Load            | Power draw on Switch 2                    | W         |
| FranklinWH Switch 2 Lifetime Use    | Total energy used by Switch 2             | Wh        |
| FranklinWH V2L Use                  | Power use via Vehicle-to-Load             | W         |
| FranklinWH V2L Import               | Total energy drawn from V2L               | Wh        |
| FranklinWH V2L Export               | Total energy delivered to V2L             | Wh        |

---

## Troubleshooting

- If no entities appear, confirm your username, password, and gateway ID.
- Check that FranklinWH cloud services are online.
- Review logs via **Settings → System → Logs** for errors containing `franklin_wh`.

---

## Contributing

Contributions are welcome! Please fork the repository and open a pull request:

👉 [https://github.com/richo/homeassistant-franklinwh.git](https://github.com/richo/homeassistant-franklinwh.git)

---

## License

This project is dual-licensed under the [MIT License](LICENSE) and the [Apache License 2.0](LICENSE).

You may choose either license when using or contributing to this project.
