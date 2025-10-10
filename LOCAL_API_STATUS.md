# Local API Status

## Current Status: ❌ NOT FUNCTIONAL

The local API feature is **currently disabled** in the integration configuration screens.

---

## Why Is It Disabled?

### Testing Results:
- ✅ Cloud API works reliably
- ❌ Local API causes timeout errors
- ❌ Gateway doesn't respond to local requests
- ⚠️ `franklinwh` Python library may not fully support local API

### User Impact:
Without disabling these fields:
- Users would see timeout errors
- Users would be confused about setup
- Users would waste time troubleshooting
- Integration would appear "broken"

---

## What Changed (v1.0.1 → v1.0.2)

### Config Flow (Setup Screen)
**BEFORE:**
```
Email Address: ___________
Password: ___________
Gateway ID: ___________
☐ Use Local API (experimental)
Local Host IP: ___________
```

**AFTER:**
```
Email Address: ___________
Password: ___________
Gateway ID: ___________

Note: Local API is currently not functional - 
only cloud polling is available.
```

### Options Flow (Configuration Screen)
**BEFORE:**
```
Update interval: [60] seconds
☐ Use Local API (experimental)
Local Host IP: ___________
```

**AFTER:**
```
Update interval: [60] seconds

Note: Local API options are disabled as they 
are not yet functional.
```

---

## Code Changes

### config_flow.py
```python
# Fields commented out but code preserved for future use
data_schema = vol.Schema({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_GATEWAY_ID): cv.string,
    # Local API not functional yet - fields shown but ignored
    # vol.Optional(CONF_USE_LOCAL_API, default=False): cv.boolean,
    # vol.Optional(CONF_LOCAL_HOST): cv.string,
})
```

### strings.json & translations/en.json
- Updated description to include notice
- Removed local API field definitions
- Updated scan interval description

---

## For Future Implementation

When local API becomes functional:

### Step 1: Test Local API
```python
# Test script needed
client = franklinwh.Client(token_fetcher, gateway_id)
# Try local connection
# Verify it works without timeout
```

### Step 2: Uncomment Fields
```python
# In config_flow.py - uncomment these lines:
vol.Optional(CONF_USE_LOCAL_API, default=False): cv.boolean,
vol.Optional(CONF_LOCAL_HOST): cv.string,
```

### Step 3: Update Strings
```json
{
  "description": "Connect your FranklinWH system...",
  "use_local_api": "Use Local API",
  "local_host": "Local Host IP Address"
}
```

### Step 4: Update Documentation
- Update README.md
- Update QUICK_START.md
- Remove experimental warnings

### Step 5: Test Thoroughly
- Test cloud API still works
- Test local API connection
- Test fallback behavior
- Test timeout handling

---

## Research Needed

To enable local API in the future:

### Questions to Answer:
1. Does FranklinWH gateway have a local API endpoint?
2. What port does it listen on?
3. Does it require authentication?
4. What protocol does it use (HTTP, MQTT, Modbus)?
5. Does firmware version matter?

### Resources:
- FranklinWH documentation (if available)
- `franklinwh-python` library source code
- Network packet capture from mobile app
- Community forum discussions
- Contact FranklinWH support

### Known Information:
- Cloud API: ✅ Works via `franklinwh` library
- Uses MQTT over cloud
- Gateway ID required
- Token-based authentication

---

## Current Configuration

### What Users See:
✅ Clean, simple setup form
✅ Only functional fields shown
✅ Clear notice about local API
✅ No confusing options
✅ No timeout errors

### What Users Get:
✅ Reliable cloud polling
✅ 60-second update interval (configurable)
✅ All sensors and switches working
✅ Stable connection
✅ No unnecessary errors

---

## Version History

| Version | Local API Status | Notes |
|---------|-----------------|-------|
| v1.0.0 | ⚠️ Experimental | Fields shown, caused timeouts |
| v1.0.1 | ⚠️ Experimental | Better error handling |
| v1.0.2 | ❌ Disabled | Fields removed from UI |

---

## Decision Rationale

### Why Disable Rather Than Fix?

1. **Library Limitation**: `franklinwh` library may not support local API
2. **Gateway Limitation**: FranklinWH gateway may not expose local API
3. **User Experience**: Better to have working cloud API than broken local API
4. **Maintainability**: Simpler code is easier to maintain
5. **Future Ready**: Code preserved in comments for easy re-enabling

### Why Keep Code in Comments?

1. **Documentation**: Shows intended functionality
2. **Easy to Re-enable**: Just uncomment when ready
3. **Version Control**: History is preserved
4. **Reference**: Helps future developers understand intent

---

## Recommendation

**For Now:**
- ✅ Use cloud polling (default)
- ✅ 60-second update interval
- ✅ Reliable and tested
- ✅ No special configuration needed

**For Future:**
- 📋 Research local API availability
- 📋 Test with real hardware
- 📋 Document local API protocol
- 📋 Update library if needed
- 📋 Re-enable fields when functional

---

## Summary

The local API feature has been **intentionally disabled** in the UI to provide a better user experience. The code is preserved in comments for future implementation when the local API becomes functional.

**Current Status**: Cloud polling only ✅
**Future Goal**: Optional local API when available 🎯

---

**Last Updated**: 2025-10-10
**Status**: Local API disabled in UI, cloud polling working

