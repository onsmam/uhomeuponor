"""DataUpdateCoordinator for Uhome Uponor: one central poll for all entities."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from logging import getLogger

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .const import (
    AUTO_RELOAD_AFTER,
    AUTO_RELOAD_COOLDOWN,
    DEFAULT_SCAN_INTERVAL,
    POLL_TIMEOUT,
    REFRESH_AFTER_WRITE_DELAY,
)
from .uponor_api import UponorAPIException, UponorClient
from .uponor_api.const import DOMAIN

_LOGGER = getLogger(__name__)

# hass.data[DOMAIN] key; survives an entry reload, so the cooldown holds across reloads
LAST_AUTO_RELOAD = "last_auto_reload"


class UponorCoordinator(DataUpdateCoordinator[None]):
    """Polls U@Home and all thermostats once per interval.

    The values stay in the UponorClient device objects; the coordinator data is
    always None. always_update therefore stays True: with False, None == None
    would suppress every listener callback.
    """

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, client: UponorClient) -> None:
        interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=REFRESH_AFTER_WRITE_DELAY, immediate=False
            ),
            always_update=True,
        )
        self.client = client
        self._failing_since = None

    async def _async_update_data(self) -> None:
        try:
            async with asyncio.timeout(POLL_TIMEOUT):
                await self.client.async_poll()
        except Exception as err:
            self._track_failure()
            if isinstance(err, (UponorAPIException, aiohttp.ClientError, TimeoutError)):
                raise UpdateFailed(f"Error communicating with Uponor gateway: {err}") from err
            raise
        self._failing_since = None

    def _track_failure(self) -> None:
        """Schedule one reload of the entry after AUTO_RELOAD_AFTER of continuous failures."""
        now = dt_util.utcnow()
        if self._failing_since is None:
            self._failing_since = now
            return
        if now - self._failing_since < AUTO_RELOAD_AFTER:
            return

        entry_id = self.config_entry.entry_id
        reloads = self.hass.data.setdefault(DOMAIN, {}).setdefault(LAST_AUTO_RELOAD, {})
        last = reloads.get(entry_id)
        if last is not None and now - last < AUTO_RELOAD_COOLDOWN:
            return

        reloads[entry_id] = now
        _LOGGER.warning(
            "Uponor gateway has not responded since %s, reloading the integration",
            dt_util.as_local(self._failing_since).strftime("%H:%M:%S"),
        )
        self.hass.config_entries.async_schedule_reload(entry_id)
