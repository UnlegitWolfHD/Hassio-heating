import logging
from typing import Any, Optional
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from ..const import DOMAIN, CONF_NAME, CONF_HEATER, CONF_COOLER
from .sensors import SensorManager
from .control import ControlLogic
from .override import OverrideHandler

_LOGGER = logging.getLogger(__name__)

class EcoThermostatEntity(ClimateEntity):
    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        data = entry.data

        self._name = data[CONF_NAME]
        self._heater = data[CONF_HEATER]
        self._cooler = data.get(CONF_COOLER)

        # Manager
        self.sensors = SensorManager(hass, data)
        self.control = ControlLogic(hass, entry, self._heater, self._cooler)
        self.override = OverrideHandler(hass, data)

        # Entity Attribute
        self._attr_name = self._name
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": self._name,
            "manufacturer": "Eco Thermostat",
            "model": "Virtual Climate",
            "sw_version": "4.0.0",
        }

        self._attr_hvac_modes = self.control.supported_modes(self._cooler)
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_preset_modes = list(self.control.presets.keys())

    # Climate Properties
    @property
    def current_temperature(self) -> Optional[float]:
        return self.sensors.current_temp

    @property
    def current_humidity(self) -> Optional[float]:
        return self.sensors.current_hum

    @property
    def hvac_mode(self) -> HVACMode:
        return self.control.hvac_mode

    @property
    def target_temperature(self) -> float:
        return self.control.target_temp

    @property
    def preset_mode(self) -> str:
        return self.control.preset_mode

    # Climate API
    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (t := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.control.set_target(t)
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.control.set_mode(hvac_mode)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.control.set_preset(preset_mode)
        self.async_write_ha_state()

    async def async_update(self):
        await self.sensors.refresh()
        await self.control.evaluate(self.sensors)
        await self.override.apply(self.control, self.sensors)
