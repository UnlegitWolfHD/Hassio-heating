import logging
from typing import Any, Optional
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature, HVACAction, PRESET_ECO, PRESET_COMFORT, PRESET_SLEEP, PRESET_AWAY
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.event import async_track_state_change_event
from .sensors import SensorManager
from .control import ControlLogic
from .override import OverrideHandler
from .const import DOMAIN, CONF_NAME, CONF_HEATER, CONF_COOLER

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the climate platform."""
    async_add_entities([EcoThermostatEntity(hass, entry)], True)

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

        # HVAC Modes
        modes = [HVACMode.OFF, HVACMode.HEAT]
        if data.get(CONF_COOLER):
            modes.append(HVACMode.COOL)
        self._attr_hvac_modes = modes

        # Preset Modes
        self._attr_preset_modes = [PRESET_ECO, PRESET_COMFORT, PRESET_SLEEP, PRESET_AWAY]

        # Features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.PRESET_MODE
        )

        self._enable_turn_on_off_backwards_compatibility = False

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
        return self.control.hvac_action

    @property
    def preset_mode(self) -> Optional[str]:
        return self.control.preset_mode

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.warning("Unsupported HVAC mode: %s", hvac_mode)
            return
        self.control.hvac_mode = hvac_mode
        await self.control.evaluate(self.sensors)
        await self.override.apply(self.control, self.sensors)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in self._attr_preset_modes:
            _LOGGER.warning("Unsupported preset mode: %s", preset_mode)
            return
        self.control.preset_mode = preset_mode
        # Update target temperature from preset
        if preset_mode in self.control.presets:
            self.control.target_temp = float(self.control.presets[preset_mode])
        await self.control.evaluate(self.sensors)
        await self.override.apply(self.control, self.sensors)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if t := kwargs.get(ATTR_TEMPERATURE):
            self.control.target_temp = float(t)
            await self.control.evaluate(self.sensors)
            await self.override.apply(self.control, self.sensors)
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()
        # Fenster-Listener
        if self.control.windows:
            async def _on_window_change(event):
                await self.async_update()
            self.async_on_remove(
                async_track_state_change_event(self.hass, self.control.windows, _on_window_change)
            )

    async def async_update(self) -> None:
        await self.sensors.refresh()
        await self.control.evaluate(self.sensors)
        await self.override.apply(self.control, self.sensors)
        self.async_write_ha_state()
