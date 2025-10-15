# AI Agent Context for FranklinWH Integration

## Quick Start Summary

**What**: Home Assistant custom integration for FranklinWH energy storage systems  
**Who**: Joshua Seidel (@JoshuaSeidel), rewritten with Claude Sonnet 4.5  
**Status**: Production ready, v1.0.7+  
**Library**: franklinwh-python 0.4.1 (PyPI - this is critical!)

## The Most Important Thing to Know

⚠️ **CRITICAL**: The franklinwh library on **PyPI is version 0.4.1**. The **GitHub repo has newer unreleased features**. Always code against 0.4.1, not GitHub master.

### What Exists in 0.4.1 (Available)
- `Client`, `TokenFetcher`, `Mode` (from `franklinwh`)
- `Stats` class (from `franklinwh.client`, NOT exported)
- Methods: `get_stats()`, `get_smart_switch_state()`, `set_smart_switch_state()`

### What Doesn't Exist in 0.4.1 (Not Available)
- `AccessoryType`, `GridStatus` enums
- Methods: `get_accessories()`, `set_grid_status()`
- Any grid control features

## Project Goals

1. **Monitor** FranklinWH battery, solar, grid, and home energy
2. **Control** smart circuit switches (3 switches)
3. **Energy Dashboard** compatibility for all energy sensors
4. **Reliability** through resilient coordinator (graceful failure handling)
5. **Modern HA** patterns (config flow, coordinator, device registry)

## Architecture at a Glance

```
User ─> Config Flow ─> Coordinator ─> franklinwh API
                            │
                            ├─> Sensors (25+ entities)
                            └─> Switches (3 smart circuits)
```

### Data Flow
1. User configures via UI (username, password, gateway ID)
2. Coordinator polls API every 60 seconds
3. Data wrapped in `FranklinWHData` with `Stats` object
4. Sensors extract values via `value_fn` lambdas
5. Energy Dashboard uses cumulative kWh sensors

## Common Pitfalls & Solutions

### ❌ DON'T: Import from wrong place
```python
from franklinwh import Stats  # WRONG - not exported
from franklinwh import AccessoryType  # WRONG - doesn't exist
```

### ✅ DO: Import correctly
```python
from franklinwh import Client, TokenFetcher
from franklinwh.client import Stats  # Correct path
```

### ❌ DON'T: Block the event loop
```python
client = franklinwh.Client(fetcher, gateway)  # WRONG - blocking
```

### ✅ DO: Use executor
```python
client = await hass.async_add_executor_job(create_client)  # Correct
```

### ❌ DON'T: Use Wh for Energy Dashboard
```python
native_unit_of_measurement=UnitOfEnergy.WATT_HOUR  # WRONG
```

### ✅ DO: Use kWh
```python
native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR  # Correct
value_fn=lambda data: data.stats.totals.switch_1_use / 1000  # Convert
```

## File Responsibilities

| File | Purpose | Key Points |
|------|---------|------------|
| `__init__.py` | Entry point | Sets up coordinator, forwards platforms |
| `config_flow.py` | UI setup | Validates credentials, wraps blocking I/O |
| `coordinator.py` | Data fetching | Polls API, handles failures, caches data |
| `sensor.py` | Sensor entities | 25+ sensors, all use coordinator data |
| `switch.py` | Switch entities | 3 smart circuit switches only |
| `const.py` | Constants | Domain name, config keys, intervals |
| `manifest.json` | Metadata | **Version**, requirements, integration type |

## When Making Changes

### Adding a Sensor
1. Check if data exists in `Stats` object
2. Add to `SENSOR_TYPES` in `sensor.py`
3. Use correct units (kWh for energy, kW for power)
4. Set proper device class and state class
5. Test in Home Assistant

### Fixing Import Errors
1. Check if class exists in franklinwh 0.4.1
2. Verify it's exported in `__init__.py`
3. Import from submodule if needed (`franklinwh.client`)
4. Remove code that depends on unavailable classes

### Bumping Version
1. Update `manifest.json` version
2. Commit with clear message
3. Create GitHub release with `gh release create`
4. Update `README.md` changelog
5. Document breaking changes

## Testing Strategy

1. **Load Test**: Does integration load without errors?
2. **Sensor Test**: Do all sensors appear and show values?
3. **Switch Test**: Can you toggle switches on/off?
4. **Energy Test**: Do sensors appear in Energy Dashboard config?
5. **Resilience Test**: What happens during network issues?
6. **Config Test**: Can you set up a new instance via UI?

## Version History Context

- **v1.0.0-1.0.3**: Initial rewrite, config flow, coordinator
- **v1.0.4**: Added features (some removed later for compatibility)
- **v1.0.5**: Fixed requirements (0.5.0 doesn't exist → 0.4.1)
- **v1.0.6**: Fixed Stats import (not exported → import from client)
- **v1.0.7**: Removed Grid Connection switch (library incompatibility)

## Resilience Features

The coordinator has a **3-failure grace period**:
- Failure 1: Log warning, return last data, stay available
- Failure 2: Log warning, return last data, stay available
- Failure 3: Log error, mark unavailable
- Success: Reset counter

This prevents flickering during temporary network issues.

## Energy Dashboard Integration

All energy sensors must have:
```python
FranklinWHSensorEntityDescription(
    key="sensor_name",
    name="Display Name",
    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,  # kWh!
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,  # Cumulative
    value_fn=lambda data: data.stats.totals.field_name,  # or / 1000
)
```

## Calculated Sensors Example

**Battery Charge from Grid** = Total Battery Charge - Solar Energy
```python
value_fn=lambda data: max(0, 
    (data.stats.totals.battery_charge or 0) - 
    (data.stats.totals.solar or 0)
) if data.stats else None
```

## Why Things Were Removed

### Grid Connection Switch (v1.0.7)
- Required `AccessoryType` and `GridStatus` classes
- These don't exist in franklinwh 0.4.1
- GitHub repo has them, but not published to PyPI
- Will restore when library is updated

## Quick Commands

```bash
# Check what's on PyPI
pip show franklinwh

# Create release
gh release create v1.0.X --title "..." --notes "..."

# Test locally in HA
cp -r . /config/custom_components/franklin_wh/
# Then restart HA

# Check logs
tail -f /config/home-assistant.log | grep franklin
```

## When You Need to Research

1. **Library features**: Check PyPI, not GitHub
2. **HA patterns**: Check Home Assistant docs
3. **User issues**: Check integration logs
4. **API data**: Use diagnostics download feature

## Success Criteria

✅ Integration loads without errors  
✅ All sensors show data  
✅ Switches can be controlled  
✅ Energy Dashboard compatibility  
✅ No blocking I/O warnings  
✅ Handles temporary failures gracefully  
✅ Version bumped and released  
✅ Documentation updated  

## Remember

This integration is a **complete rewrite** focused on:
- Modern Home Assistant architecture
- Compatibility with published library versions
- Resilience and reliability
- Energy Dashboard integration

**Always validate against franklinwh 0.4.1 from PyPI, not GitHub!**

