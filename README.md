# Franklin WH

This implements a collection of sensors, and a switch implementation for the Franklin WH home energy system.

The most basic sensors are currently shown in this screenshot

![image](https://github.com/slackwilson/homeassistant-franklinwh/assets/109522242/e9d0dd64-dde2-4d40-b0ce-42c108e56086)


# Prerequisites

You'll need an your ID (serial number)

The ID is available from the franklin app under More -> Site Address. It's shown as your Serial Number.

# Installation


One way to do this is to use the web terminal from the [Advanced SSH & Web Terminal add-on](https://github.com/hassio-addons/addon-ssh)

Within the terminal screen, paste the following command. This command clones the files into the correct folder on your system `<config_dir>/custom_components/franklin_wh/`
```
git clone https://github.com/richo/homeassistant-franklinwh config/custom_components/franklin_wh
```

If you see no errors similar to the follwing, you're done with the file installation
![image](https://github.com/slackwilson/homeassistant-franklinwh/assets/109522242/8cf66ea9-3947-4f47-91aa-d6da1b2621e1)



# Configuration

To add the basic sensors to your home assitant add the following to your `configuration.yaml` file:

It is very strongly recommended to put your password in secrets.yaml to avoid accidentally revealing it.

Example sensors configuration.yaml entry.

```yaml
sensor:
  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: 1005xxxxxxxxxxx
```

The ID is available from the franklin app under More -> Site Address. It's shown as your Serial Number.

## Switches

And to add switches, see below as an example, The switches in the example is the smart circuits that should be
bound to that virtual switch.


```yaml
switch:
  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: 1005xxxxxxxxxxx
    switches: [3]
    name: "FWH switch1"
  - platform: franklin_wh
    username: "email@domain.com"
    password: !secret franklinwh_password
    id: 1005xxxxxxxxxxx
    switches: [1, 2]
    name: "FWH switch2"
```

# Post Configuration
Do a full restart of Home Assistant to enable the addon.


