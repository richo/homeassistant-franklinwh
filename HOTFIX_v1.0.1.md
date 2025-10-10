# Hotfix v1.0.1 - Blocking Call Fix

## Issue
Home Assistant 2024.x with Python 3.13 has stricter async event loop protection. The `franklinwh.Client()` constructor was performing blocking I/O operations:
- SSL certificate loading (`load_verify_locations`)
- HTTP requests (`putrequest`)

These blocking calls caused runtime errors when called directly in async functions.

## Root Cause
```python
# BAD - Blocks the event loop
client = franklinwh.Client(token_fetcher, gateway_id)
```

The `franklinwh` library uses synchronous `requests` library which performs blocking I/O operations during client initialization.

## Solution
Wrapped all `franklinwh.Client()` initialization calls in `async_add_executor_job()`:

### 1. Config Flow (config_flow.py)
```python
# GOOD - Runs in executor thread
def create_client():
    token_fetcher = franklinwh.TokenFetcher(username, password)
    return franklinwh.Client(token_fetcher, gateway_id)

client = await hass.async_add_executor_job(create_client)
```

### 2. Coordinator (coordinator.py)
Implemented lazy client initialization:
- Client is `None` in `__init__`
- Created on first `_async_update_data()` call
- Uses executor to avoid blocking

```python
# In __init__
self.client = None
self._client_lock = False

# In _async_update_data
if self.client is None and not self._client_lock:
    self._client_lock = True
    def create_client():
        token_fetcher = TokenFetcher(self.username, self.password)
        return Client(token_fetcher, self.gateway_id)
    
    self.client = await self.hass.async_add_executor_job(create_client)
```

## Files Changed
- `config_flow.py` - Wrapped client creation in executor
- `coordinator.py` - Lazy client initialization in executor

## Testing
After updating:
1. Restart Home Assistant
2. Add FranklinWH integration through UI
3. Verify no blocking call warnings in logs
4. Confirm sensors update correctly

## For Users
**To apply this fix:**

### Option 1: HACS (Recommended)
1. Go to HACS → Integrations
2. Find FranklinWH
3. Click "Update" (when available)
4. Restart Home Assistant

### Option 2: Manual Update
```bash
cd /config/custom_components/franklin_wh/
curl -O https://raw.githubusercontent.com/JoshuaSeidel/homeassistant-franklinwh/main/config_flow.py
curl -O https://raw.githubusercontent.com/JoshuaSeidel/homeassistant-franklinwh/main/coordinator.py
# Restart Home Assistant
```

### Option 3: Git Pull (if installed via git)
```bash
cd /config/custom_components/franklin_wh/
git pull
# Restart Home Assistant
```

## Impact
- ✅ Fixes blocking call errors
- ✅ No breaking changes
- ✅ No user configuration changes needed
- ✅ Compatible with existing setups

## Version
- Fixed in: v1.0.1 (commit 9b152a9)
- Affected versions: v1.0.0
- Python: 3.13+
- Home Assistant: 2024.x+

## Related
- Home Assistant Async Best Practices: https://developers.home-assistant.io/docs/asyncio_blocking_operations/
- Issue: Blocking call to putrequest/load_verify_locations

---

**Status**: ✅ Fixed and pushed to GitHub

