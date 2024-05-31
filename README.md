# Franklin WH

This implements a collection of sensors, and a switch implementation for the Franklin WH home energy system.

### Installation

The install requires you to copy this folder to `<config_dir>/custom_components/franklin_wh/`. One way to do this is to use the web terminal from the [Advanced SSH & Web Terminal add-on](https://github.com/hassio-addons/addon-ssh)

Within the terminal screen, paste the following commands

cd config/custom_components
git clone https://github.com/richo/homeassistant-franklinwh
mv homeassistant-franklinwh franklin_wh




Add the following to your `configuration.yaml` file:

# Example configuration.yaml entry

```yaml
switch:
  - platform: franklin_wh
    access_token: !secret franklin_wh_token
    id: 1005xxxxxxxxxxx
    switches: [3]
    name: "test switch"
  - platform: franklin_wh
    access_token: !secret franklin_wh_token
    id: 1005xxxxxxxxxxx
    switches: [1, 2]
    name: "EV Charger"

sensor:
  - platform: franklin_wh
    access_token: !secret franklin_wh_token
    id: 1005xxxxxxxxxxx
```

You can get the access token with the script bundled in the franklinwh python
module, the ID is available from the app and will also be spat out from that
python script when I figure out an easy way to get it.

The switches list in the switch config is the smart circuits that should be
bound to that virtual switch.
