"""Uponor U@Home integration

For more details about this platform, please refer to the documentation at
https://github.com/fcastroruiz/uhomeuponor
"""
from logging import getLogger
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform, CONF_HOST, CONF_PREFIX
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from .const import CONF_SUPPORTS_COOLING, CONF_SUPPORTS_HEATING
from .coordinator import UponorCoordinator
from .uponor_api.const import DOMAIN
from .uponor_api import UponorClient

_LOGGER = getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.CLIMATE]

# If the integration does not support YAML configuration, declare this
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Options that are copied to config_entry.data. scan_interval stays in options only.
DATA_KEYS = (CONF_HOST, CONF_PREFIX, CONF_SUPPORTS_HEATING, CONF_SUPPORTS_COOLING)
# Options that change the identity of devices/entities (CONF_PREFIX is part of every
# unique_id); only a change of these clears the device and entity registry
IDENTITY_KEYS = (CONF_HOST, CONF_PREFIX)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = config.get(DOMAIN) or {}
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up this integration using UI."""
    _LOGGER.info("Loading setup entry")

    _apply_options(hass, config_entry)

    host = config_entry.data[CONF_HOST]
    session = async_get_clientsession(hass)

    uponor = UponorClient(hass=hass, server=host, session=session)
    try:
        # timeout=60: full rescan does module + N controllers + M thermostats requests
        # Each aiohttp request has total=10s timeout, so with 2 controllers and
        # 12 thermostats in batches this can take 15-30s. 8s was too short.
        await asyncio.wait_for(uponor.rescan(), timeout=60.0)
    except asyncio.CancelledError:
        raise
    except (asyncio.TimeoutError, TimeoutError) as err:
        _LOGGER.warning("Timeout connecting to Uponor gateway at %s, will retry", host)
        raise ConfigEntryNotReady(f"Timeout connecting to Uponor gateway at {host}") from err
    except Exception as err:
        _LOGGER.warning("Failed to connect to Uponor gateway at %s: %s, will retry", host, err)
        raise ConfigEntryNotReady(f"Cannot connect to Uponor gateway at {host}: {err}") from err

    coordinator = UponorCoordinator(hass, config_entry, uponor)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": uponor,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(config_entry.add_update_listener(async_update_options))
    
    return True

def _apply_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Copy the connection options to data; clear the registry only on an identity change."""
    if not config_entry.options:
        return

    new_data = {**config_entry.data}
    for key in DATA_KEYS:
        if key in config_entry.options:
            new_data[key] = config_entry.options[key]
    if new_data == dict(config_entry.data):
        return

    if any((config_entry.data.get(key) or "") != (new_data.get(key) or "") for key in IDENTITY_KEYS):
        _LOGGER.info("Host or prefix changed, recreating devices and entities")
        device_registry.async_get(hass).async_clear_config_entry(config_entry.entry_id)
        entity_registry.async_get(hass).async_clear_config_entry(config_entry.entry_id)

    hass.config_entries.async_update_entry(config_entry, data=new_data)

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug("Update setup entry: %s, data: %s, options: %s", entry.entry_id, entry.data, entry.options)
    # Unload first to ensure clean state (if loaded), then reload
    if entry.state in (ConfigEntryState.LOADED, ConfigEntryState.SETUP_RETRY):
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading setup entry: %s, data: %s, options: %s", config_entry.entry_id, config_entry.data, config_entry.options)
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
    return unload_ok
