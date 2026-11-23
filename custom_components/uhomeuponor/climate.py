"""Uponor U@Home integration
Exposes Climate control entities for Uponor thermostats

- UponorThermostat
"""

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode, PRESET_COMFORT, PRESET_ECO, PRESET_AWAY, HVACAction, ClimateEntityFeature)
from homeassistant.const import (ATTR_TEMPERATURE, CONF_PREFIX, PRECISION_TENTHS, UnitOfTemperature)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from logging import getLogger

from .const import CONF_SUPPORTS_COOLING, CONF_SUPPORTS_HEATING
from .coordinator import UponorCoordinator
from .uponor_api.const import (DOMAIN, UHOME_MODE_HEAT, UHOME_MODE_COOL, UHOME_MODE_ECO, UHOME_MODE_COMFORT)

ATTR_TECHNICAL_ALARM = "technical_alarm"
ATTR_RF_SIGNAL_ALARM = "rf_alarm"
ATTR_BATTERY_ALARM = "battery_alarm"
ATTR_REMOTE_ACCESS_ALARM = "remote_access_alarm"
ATTR_DEVICE_LOST_ALARM = "device_lost_alarm"

_LOGGER = getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    _LOGGER.info("init setup climate platform for id: %s data: %s, options: %s", config_entry.entry_id, config_entry.data, config_entry.options)
    config = config_entry.data
    prefix = config.get(CONF_PREFIX, "")
    supports_heating = config.get(CONF_SUPPORTS_HEATING, True)
    supports_cooling = config.get(CONF_SUPPORTS_COOLING, True)

    uponor = hass.data[DOMAIN][config_entry.entry_id]["client"]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_add_entities([UponorThermostat(coordinator, prefix, uponor, thermostat, supports_heating, supports_cooling)
                  for thermostat in uponor.thermostats])
    
    _LOGGER.info("finish setup climate platform for Uhome Uponor")
    return True

class UponorThermostat(CoordinatorEntity[UponorCoordinator], ClimateEntity):
    """HA Thermostat climate entity. Utilizes Uponor U@Home API to interact with U@Home"""

    def __init__(self, coordinator, prefix, uponor_client, thermostat, supports_heating, supports_cooling):
        super().__init__(coordinator)
        self.prefix = prefix
        self.uponor_client = uponor_client
        self.thermostat = thermostat
        self.supports_heating = supports_heating
        self.supports_cooling = supports_cooling
        self.device_name = f"{prefix or ''}{thermostat.by_name('room_name').value}"
        self.device_id = f"{prefix or ''}controller{str(thermostat.controller_index)}_thermostat{str(thermostat.thermostat_index)}"
        self.identity = f"{prefix or ''}controller{str(thermostat.controller_index)}_thermostat{str(thermostat.thermostat_index)}_thermostat"

    @property
    def device_info(self) -> dict:
        """Return info for device registry."""
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.device_name,
        }

    # ** Generic **
    @property
    def name(self):
        return f"{self.prefix or ''}{self.thermostat.by_name('room_name').value}"

    @property
    def unique_id(self):
        return self.identity

    @property
    def available(self):
        return super().available and self.thermostat.is_valid()

    # ** Static **
    @property
    def native_temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def precision(self):
        return PRECISION_TENTHS

    @property
    def target_temperature_step(self):
        return 0.5

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE

    @property
    def hvac_modes(self):
        modes = []

        if self.supports_heating:
            modes.append(HVACMode.HEAT)

        if self.supports_cooling:
            modes.append(HVACMode.COOL)

        return modes

    @property
    def preset_modes(self):
        return [PRESET_ECO, PRESET_AWAY, PRESET_COMFORT]

    # ** State **
    @property
    def current_humidity(self):
        return self.thermostat.by_name('rh_value').value

    @property
    def native_current_temperature(self):
        return self.thermostat.by_name('room_temperature').value

    @property
    def native_target_temperature(self):
        return self.thermostat.by_name('room_setpoint').value

    # Home Assistant versions without the native_* climate API read these names.
    # Versions with that API use the native_* members when a class provides both,
    # without a deprecation warning.
    @property
    def temperature_unit(self):
        return self.native_temperature_unit

    @property
    def current_temperature(self):
        return self.native_current_temperature

    @property
    def target_temperature(self):
        return self.native_target_temperature

    @property
    def extra_state_attributes(self):
        return {
            ATTR_TECHNICAL_ALARM: self.thermostat.by_name(ATTR_TECHNICAL_ALARM).value,
            ATTR_RF_SIGNAL_ALARM: self.thermostat.by_name(ATTR_RF_SIGNAL_ALARM).value,
            ATTR_BATTERY_ALARM: self.thermostat.by_name(ATTR_BATTERY_ALARM).value,
            ATTR_REMOTE_ACCESS_ALARM: self.uponor_client.uhome.by_name(ATTR_REMOTE_ACCESS_ALARM).value,
            ATTR_DEVICE_LOST_ALARM: self.uponor_client.uhome.by_name(ATTR_DEVICE_LOST_ALARM).value
        }
        
    @property
    def preset_mode(self):
        if self.uponor_client.uhome.by_name('forced_eco_mode').value == 1:
            return PRESET_AWAY

        return PRESET_COMFORT

    @property
    def hvac_mode(self):
        if self.uponor_client.uhome.by_name('hc_mode').value == 1:
            return HVACMode.COOL

        return HVACMode.HEAT

    @property
    def hvac_action(self):
        if self.thermostat.by_name('room_in_demand').value == 0:
            return HVACAction.IDLE
        
        if self.hvac_mode == HVACMode.HEAT:
            return HVACAction.HEATING
        else:
            return HVACAction.COOLING

    # ** Actions **
    # set_values() applies the new value locally; the delayed refresh reads back
    # what the gateway actually stored, for all entities at once.
    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.HEAT:
            value = UHOME_MODE_HEAT
        else:
            value = UHOME_MODE_COOL
        await self.thermostat.set_hvac_mode(value)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    # Support setting preset_mode
    async def async_set_preset_mode(self, preset_mode):
        if preset_mode == PRESET_ECO:
            # ECO toggles: if away, go comfort; if comfort, go away
            if self.uponor_client.uhome.by_name('forced_eco_mode').value == 1:
                value = UHOME_MODE_COMFORT
            else:
                value = UHOME_MODE_ECO
        elif preset_mode == PRESET_AWAY:
            value = UHOME_MODE_ECO
        else:
            value = UHOME_MODE_COMFORT
        await self.thermostat.set_preset_mode(value)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs):
        if kwargs.get(ATTR_TEMPERATURE) is None:
            return
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self.thermostat.set_setpoint(temperature)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
            
