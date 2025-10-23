import logging
from typing import Any, Optional
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature, HVACAction
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.event import async_track_state_change_event
from .sensors import SensorManager
from .control import ControlLogic
from .override import OverrideHandler
from .const import DOMAIN, CONF_NAME, CONF_HEATER, CONF_COOLER

_LOGGER = logging.getLogger(__name__)

class EcoThermostatEntity(ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        data = entry.data
        self._attr_name = data[CONF_NAME]
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"
        self.sensors = SensorManager(hass, data)
        self.control = ControlLogic(hass, entry, data[CONF_HEATER], data.get(CONF_COOLER))
        self.override = OverrideHandler(hass, data)
        self._attr_hvac_modes = self.control.presets and [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        # Fenster-Listener
        if self.control.windows:
            async def _on_window_change(event):
                await self.async_update()
            async_track_state_change_event(hass, self.control.windows, _on_window_change)

    @property
    def current_temperature(self) -> Optional[float]:
        return self.sensors.current_temp

    @property
    def target_temperature(self) -> Optional[float]:
        return self.control.target_temp

    @property
    def hvac_mode(self) -> HVACMode:
        return self.control.hvac_mode

    @property
    def hvac_action(self) -> HVACAction:
        ct = self.sensors.current_temp
        if ct is None:
            return HVACAction.IDLE
        if self.control.hvac_mode == HVACMode.HEAT and ct < self.control.target_temp:
            return HVACAction.HEATING
        if self.control.hvac_mode == HVACMode.COOL and ct > self.control.target_temp:
            return HVACAction.COOLING
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if t := kwargs.get(ATTR_TEMPERATURE):
            self.control.target_temp = float(t)
            await self.override.apply(self.control, self.sensors)
            self.async_write_ha_state()

    async def async_update(self) -> None:
        await self.sensors.refresh()
        await self.control.evaluate(self.sensors)
        await self.override.apply(self.control, self.sensors)
        self.async_write_ha_state()
