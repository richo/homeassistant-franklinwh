# GitHub Copilot Instructions - FranklinWH Integration

## Project Context

You are working on a **Home Assistant custom integration** for FranklinWH energy storage systems. This integration monitors battery, solar, grid, and home energy, and controls smart circuit switches.

**Critical Information:**
- **Author**: Joshua Seidel (@JoshuaSeidel)
- **Library**: franklinwh-python **version 0.4.1 from PyPI** (not GitHub master!)
- **Architecture**: Modern Home Assistant with config flow, DataUpdateCoordinator, device registry
- **Current Version**: 1.0.7+

## ⚠️ CRITICAL CONSTRAINT

The `franklinwh` library on **PyPI is version 0.4.1**. The GitHub repository has newer features that are **NOT published**. You MUST code against 0.4.1.

### Available in 0.4.1 ✅
```python
from franklinwh import Client, TokenFetcher, Mode
from franklinwh.client import Stats  # Not exported in __init__.py!
```

### NOT Available in 0.4.1 ❌
```python
# These don't exist in 0.4.1 - DO NOT USE
from franklinwh import Stats  # Not exported
from franklinwh import AccessoryType, GridStatus  # Don't exist
client.get_accessories()  # Method doesn't exist
client.set_grid_status()  # Method doesn't exist
```

## Code Generation Rules

### 1. Imports - Always Check Library Version
```python
# ✅ CORRECT
from franklinwh import Client, TokenFetcher
from franklinwh.client import Stats

# ❌ WRONG - Will cause ImportError
from franklinwh import Stats, AccessoryType, GridStatus
```

### 2. Async I/O - Never Block the Event Loop
```python
# ✅ CORRECT - Use executor for blocking calls
def create_client():
    token_fetcher = TokenFetcher(username, password)
    return Client(token_fetcher, gateway_id)

client = await hass.async_add_executor_job(create_client)
stats = await hass.async_add_executor_job(client.get_stats)

# ❌ WRONG - Blocks event loop
client = Client(TokenFetcher(username, password), gateway_id)
stats = client.get_stats()
```

### 3. Energy Sensors - Use kWh, Not Wh
```python
# ✅ CORRECT - Energy Dashboard compatible
FranklinWHSensorEntityDescription(
    key="sensor_key",
    name="Sensor Name",
    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    value_fn=lambda data: (data.stats.totals.field_name / 1000) if data.stats else None,
)

# ❌ WRONG - Won't work with Energy Dashboard
native_unit_of_measurement=UnitOfEnergy.WATT_HOUR
```

### 4. Error Handling - Be Resilient
```python
# ✅ CORRECT - Graceful degradation
try:
    return self.entity_description.value_fn(self.coordinator.data)
except (AttributeError, TypeError, KeyError) as err:
    _LOGGER.debug("Error getting value for %s: %s", self.key, err)
    return None
```

### 5. Unique IDs - Consistent Pattern
```python
# ✅ CORRECT
self._attr_unique_id = f"{gateway_id}_{description.key}"

# Device identifiers
DeviceInfo(
    identifiers={(DOMAIN, gateway_id)},
    name=f"FranklinWH {gateway_id[-6:]}",
    manufacturer=MANUFACTURER,
    model=MODEL,
)
```

## API Data Structure Reference

When accessing coordinator data:

```python
# Current (instantaneous) values
data.stats.current.battery_soc          # float (0-100) %
data.stats.current.battery_use          # float (kW) + = discharge, - = charge
data.stats.current.home_load            # float (kW)
data.stats.current.grid_use             # float (kW) + = export, - = import
data.stats.current.solar_production     # float (kW)
data.stats.current.generator_production # float (kW)
data.stats.current.switch_1_load        # float (W)
data.stats.current.switch_2_load        # float (W)
data.stats.current.v2l_use              # float (W)

# Totals (cumulative) values
data.stats.totals.battery_charge    # float (kWh)
data.stats.totals.battery_discharge # float (kWh)
data.stats.totals.grid_import       # float (kWh)
data.stats.totals.grid_export       # float (kWh)
data.stats.totals.solar             # float (kWh)
data.stats.totals.generator         # float (kWh)
data.stats.totals.switch_1_use      # float (Wh) - convert to kWh!
data.stats.totals.switch_2_use      # float (Wh) - convert to kWh!
data.stats.totals.v2l_import        # float (Wh) - convert to kWh!
data.stats.totals.v2l_export        # float (Wh) - convert to kWh!

# Switch state
data.switch_state  # tuple[bool, bool, bool] for switches 1, 2, 3
```

## File Structure & Responsibilities

```
custom_components/franklin_wh/
├── __init__.py           # Integration entry, coordinator setup
├── config_flow.py        # UI configuration flow
├── coordinator.py        # DataUpdateCoordinator, API polling
├── sensor.py            # 25+ sensor entities
├── switch.py            # 3 smart circuit switches
├── const.py             # Constants (DOMAIN, config keys, etc.)
├── manifest.json        # Metadata, version, requirements
├── strings.json         # UI strings
└── translations/
    └── en.json          # English translations
```

## Common Patterns

### Adding a New Sensor
```python
FranklinWHSensorEntityDescription(
    key="unique_sensor_key",
    name="Display Name",
    native_unit_of_measurement=UNIT,
    device_class=SensorDeviceClass.XXXX,
    state_class=SensorStateClass.XXXX,
    value_fn=lambda data: data.stats.current.field_name if data.stats else None,
),
```

### Creating Calculated Sensors
```python
# Example: Battery charged from grid = Total charge - Solar
value_fn=lambda data: (
    max(0, (data.stats.totals.battery_charge or 0) - (data.stats.totals.solar or 0))
    if data.stats else None
),
```

### Entity Availability Check
```python
@property
def available(self) -> bool:
    """Return if entity is available."""
    return (
        super().available
        and self.coordinator.data is not None
        and self.coordinator.data.stats is not None
    )
```

## Testing Requirements

Before suggesting code changes, ensure:
- [ ] No blocking I/O in async functions
- [ ] Correct imports from franklinwh 0.4.1
- [ ] Energy sensors use kWh (not Wh)
- [ ] Proper error handling (try/except with logging)
- [ ] Type hints for all functions
- [ ] Entity unique IDs follow pattern
- [ ] Device info properly set

## Version Management

When suggesting version changes:
1. Update `manifest.json` version field
2. Suggest commit message format: `type: description`
3. Remind about creating GitHub release
4. Suggest updating `README.md` changelog

## Known Limitations

DO NOT suggest these features (require unreleased library):
- Grid Connection switch control
- AccessoryType or GridStatus usage
- Operation mode changes via API
- Battery reserve control via API
- Local API features (not functional)

## Coordinator Resilience

The coordinator has a 3-failure grace period:
```python
# First 2 failures: Return last known data, stay available
# 3rd failure: Mark unavailable
self._consecutive_failures = 0
self._max_failures = 3
```

## Energy Dashboard Compatibility

All energy sensors MUST have:
```python
native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR
device_class=SensorDeviceClass.ENERGY
state_class=SensorStateClass.TOTAL_INCREASING
```

## Code Style

- Follow Home Assistant coding standards
- Use async/await for all I/O operations
- Type hints for all function parameters and returns
- Comprehensive error handling with `_LOGGER.debug/warning/error`
- Clear, descriptive variable names
- Comments for complex logic only

## Quick Reference

```python
# Domain
DOMAIN = "franklin_wh"

# Config keys
CONF_GATEWAY_ID = "gateway_id"
CONF_USERNAME = from homeassistant.const
CONF_PASSWORD = from homeassistant.const

# Update intervals
DEFAULT_SCAN_INTERVAL = 60  # seconds (cloud)
DEFAULT_LOCAL_SCAN_INTERVAL = 10  # seconds (local - not functional)

# Library version on PyPI
FRANKLINWH_VERSION = "0.4.1"
```

## When in Doubt

1. Check if feature exists in franklinwh 0.4.1 (not GitHub)
2. Wrap blocking I/O in `async_add_executor_job`
3. Use kWh for energy (not Wh)
4. Handle errors gracefully
5. Test imports before suggesting

## Remember

This integration prioritizes:
- **Compatibility** with published library versions
- **Reliability** through resilient error handling
- **User Experience** with modern HA patterns
- **Energy Dashboard** integration

Always code against franklinwh 0.4.1 from PyPI, not GitHub master!

