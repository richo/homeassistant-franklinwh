# Franklin WH

This implements a collection of sensors, and a switch implementation for the Franklin WH home energy system.

The most basic sensors are currently shown in this screenshot

![image](https://github.com/slackwilson/homeassistant-franklinwh/assets/109522242/e9d0dd64-dde2-4d40-b0ce-42c108e56086)


# Prerequisites

You'll need an your ID (serial number)

The ID is available from the franklin app under More -> Site Address. It's shown as your Serial Number.

# Installation

FranklinWH is moving to HACS! It should be simple enough, but I'm still figuring it out. So for now it's a bit of a mystery.

# Installation (Non-HACS)

Installing outside of HACS still works, although it's a little more involved than before.

One way to do this is to use the web terminal from the [Advanced SSH & Web Terminal add-on](https://github.com/hassio-addons/addon-ssh)

You'll need to clone the repo somewhere, and then symlink the `custom_components/franklin_wh` directory into `config/custom_components/franklin_wh`

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


