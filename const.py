"""Constants for the FranklinWH integration."""
from typing import Final

DOMAIN: Final = "franklin_wh"

# Configuration
CONF_GATEWAY_ID: Final = "gateway_id"
CONF_USE_LOCAL_API: Final = "use_local_api"
CONF_LOCAL_HOST: Final = "local_host"

# Default values
DEFAULT_NAME: Final = "FranklinWH"
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
DEFAULT_LOCAL_SCAN_INTERVAL: Final = 10  # seconds for local API

# API endpoints (for local API when available)
LOCAL_API_PORT: Final = 8080
LOCAL_API_TIMEOUT: Final = 10

# Device info
MANUFACTURER: Final = "FranklinWH"
MODEL: Final = "aPower/aGate Energy Storage System"

# Attributes
ATTR_GATEWAY_ID: Final = "gateway_id"
ATTR_BATTERY_SOC: Final = "battery_soc"
ATTR_BATTERY_USE: Final = "battery_use"
ATTR_HOME_LOAD: Final = "home_load"
ATTR_GRID_USE: Final = "grid_use"
ATTR_SOLAR_PRODUCTION: Final = "solar_production"
ATTR_GENERATOR_PRODUCTION: Final = "generator_production"

# Services
SERVICE_SET_OPERATION_MODE: Final = "set_operation_mode"
SERVICE_SET_BATTERY_RESERVE: Final = "set_battery_reserve"

# Operation modes
MODE_SELF_USE: Final = "self_use"
MODE_BACKUP: Final = "backup"
MODE_TIME_OF_USE: Final = "time_of_use"
MODE_CLEAN_BACKUP: Final = "clean_backup"

OPERATION_MODES: Final = [
    MODE_SELF_USE,
    MODE_BACKUP,
    MODE_TIME_OF_USE,
    MODE_CLEAN_BACKUP,
]

