"""Uponor U@Home integration
Exposes Sensors for Uponor devices, such as:

- Temperature (UponorThermostatTemperatureSensor)
- Humidity (UponorThermostatHumiditySensor)
- Battery (UponorThermostatBatterySensor)
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass, SensorEntity
from homeassistant.const import CONF_PREFIX, UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from logging import getLogger

from .coordinator import UponorCoordinator
from .uponor_api.const import (DOMAIN, UNIT_BATTERY, UNIT_HUMIDITY)

_LOGGER = getLogger(__name__)

# Read-only entities, all data comes from the coordinator
PARALLEL_UPDATES = 0


async def async_setup_entry(hass, config_entry, async_add_entities):
    _LOGGER.info("init setup sensor platform for id: %s data: %s, options: %s", config_entry.entry_id, config_entry.data, config_entry.options)
    config = config_entry.data
    prefix = config.get(CONF_PREFIX, "")

    uponor = hass.data[DOMAIN][config_entry.entry_id]["client"]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_add_entities([UponorThermostatTemperatureSensor(coordinator, prefix, uponor, thermostat)
                  for thermostat in uponor.thermostats])

    async_add_entities([UponorThermostatHumiditySensor(coordinator, prefix, uponor, thermostat)
                  for thermostat in uponor.thermostats])

    async_add_entities([UponorThermostatBatterySensor(coordinator, prefix, uponor, thermostat)
                  for thermostat in uponor.thermostats])

    _LOGGER.info("finish setup sensor platform for Uhome Uponor")
    return True

class UponorThermostatTemperatureSensor(CoordinatorEntity[UponorCoordinator], SensorEntity):
    """HA Temperature sensor entity. Utilizes Uponor U@Home API to interact with U@Home"""

    def __init__(self, coordinator, prefix, uponor_client, thermostat):
        super().__init__(coordinator)
        self.prefix = prefix
        self.uponor_client = uponor_client
        self.thermostat = thermostat
        self.device_name = f"{prefix or ''}{thermostat.by_name('room_name').value}"
        self.device_id = f"{prefix or ''}controller{thermostat.controller_index}_thermostat{thermostat.thermostat_index}"
        self.identity = f"{prefix or ''}controller{thermostat.controller_index}_thermostat{thermostat.thermostat_index}_temp"

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
    def icon(self):
        return 'mdi:thermometer'

    @property
    def available(self):
        return super().available and self.thermostat.is_valid()

    # ** DEBUG PROPERTY  **
    # @property
    # def extra_state_attributes(self):
    #     """Return the device state attributes."""
    #     attr = self.thermostat.attributes() + self.uponor_client.uhome.attributes()
    #     return {
    #         ATTR_ATTRIBUTION: attr,
    #     }

    # ** Static **
    @property
    def native_unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    # ** State **
    @property
    def native_value(self):
        return self.thermostat.by_name('room_temperature').value


class UponorThermostatHumiditySensor(CoordinatorEntity[UponorCoordinator], SensorEntity):
    """HA Humidity sensor entity. Utilizes Uponor U@Home API to interact with U@Home"""

    def __init__(self, coordinator, prefix, uponor_client, thermostat):
        super().__init__(coordinator)
        self.prefix = prefix
        self.uponor_client = uponor_client
        self.thermostat = thermostat
        self.device_name = f"{prefix or ''}{thermostat.by_name('room_name').value}"
        self.device_id = f"{prefix or ''}controller{thermostat.controller_index}_thermostat{thermostat.thermostat_index}"
        self.identity = f"{prefix or ''}controller{thermostat.controller_index}_thermostat{thermostat.thermostat_index}_rh"

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
        return f"{self.prefix or ''}{self.thermostat.by_name('room_name').value} Humidity"

    @property
    def unique_id(self):
        return self.identity

    @property
    def icon(self):
        return 'mdi:water-percent'

    @property
    def available(self):
        return super().available and self.thermostat.is_valid()

    # ** Static **
    @property
    def native_unit_of_measurement(self):
        return UNIT_HUMIDITY

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    # ** State **
    @property
    def native_value(self):
        return self.thermostat.by_name('rh_value').value


class UponorThermostatBatterySensor(CoordinatorEntity[UponorCoordinator], SensorEntity):
    """HA Battery sensor entity. Utilizes Uponor U@Home API to interact with U@Home"""

    def __init__(self, coordinator, prefix, uponor_client, thermostat):
        super().__init__(coordinator)
        self.prefix = prefix
        self.uponor_client = uponor_client
        self.thermostat = thermostat
        self.device_name = f"{prefix or ''}{thermostat.by_name('room_name').value}"
        self.device_id = f"{prefix or ''}controller{thermostat.controller_index}_thermostat{thermostat.thermostat_index}"
        self.identity = f"{prefix or ''}controller{thermostat.controller_index}_thermostat{thermostat.thermostat_index}_batt"

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
        return f"{self.prefix or ''}{self.thermostat.by_name('room_name').value} Battery"

    @property
    def unique_id(self):
        return self.identity

    @property
    def available(self):
        return super().available and self.thermostat.is_valid()

    # ** Static **
    @property
    def native_unit_of_measurement(self):
        return UNIT_BATTERY

    @property
    def device_class(self):
        return SensorDeviceClass.BATTERY

    # ** State **
    @property
    def native_value(self):
        # If there is a battery alarm, report a low level - else report 100%
        if self.thermostat.by_name('battery_alarm').value == 1:
            return 10

        return 100
