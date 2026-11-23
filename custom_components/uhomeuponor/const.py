"""Integration-level constants for Uhome Uponor."""
from datetime import timedelta

CONF_SUPPORTS_HEATING = "supports_heating"
CONF_SUPPORTS_COOLING = "supports_cooling"

# Polling interval (seconds), stored in config_entry.options only
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 600

# Upper bound for one complete poll (4 requests on a slow gateway, incl. retries)
POLL_TIMEOUT = 90

# Wait after a write before re-reading, so the gateway has applied the new value.
# Writes within this window are combined into one refresh.
REFRESH_AFTER_WRITE_DELAY = 3

# Reload the config entry once the gateway has failed for this long without
# interruption, at most once per AUTO_RELOAD_COOLDOWN
AUTO_RELOAD_AFTER = timedelta(minutes=10)
AUTO_RELOAD_COOLDOWN = timedelta(minutes=30)
