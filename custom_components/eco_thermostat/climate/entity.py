import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from ..const import DOMAIN, CONF_NAME, CONF_HEATER, CONF_COOLER
from .sensors import SensorManager
from .control import ControlLogic
from .override import OverrideHandler

_LOGGER = logging.getLogger(__name__)


class EcoThermostatEntity(ClimateEntity):
    """Virtuelles Thermostat mit Eco-/Komfort-Logik."""

    _attr_should_poll = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        data = entry.data

        # Basis-Infos
        self._name: str = data[CONF_NAME]
        self._heater: str = data[CONF_HEATER]
        self._cooler: Optional[str] = data.get(CONF_COOLER)

        # Manager / Logik
        self.sensors = SensorManager(hass, data)
        self.control = ControlLogic(hass, entry, self._heater, self._cooler)
        self.override = OverrideHandler(hass, data)

        # Entity-Attribute
        self._attr_name = self._name
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": self._name,
            "manufacturer": "Eco Thermostat",
            "model": "Virtual Climate",
            "sw_version": "4.0.0",
        }

        self._attr_hvac_modes = self.control.supported_modes()
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        self._attr_preset_modes = list(self.control.presets.keys())

    # ---------------- Climate Properties ----------------
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

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        """Gibt den aktuellen Heiz/Kühl-Status zurück."""
        ct = self.sensors.current_temp
        if ct is None:
            return HVACAction.IDLE

        if self.control.hvac_mode == HVACMode.HEAT and ct < self.control.target_temp - self.control.deadband:
            return HVACAction.HEATING
        if self.control.hvac_mode == HVACMode.COOL and ct > self.control.target_temp + self.control.deadband:
            return HVACAction.COOLING
        return HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {
            "preset_mode": self.control.preset_mode,
            "available_presets": list(self.control.presets.keys()),
            "current_humidity": self.sensors.current_hum,
            "override_climate": getattr(self.override, "override_climate", None),
            "override_entity": getattr(self.override, "override_entity", None),
        }
        # Filtere None-Werte
        return {k: v for k, v in attrs.items() if v is not None}

    # ---------------- Climate API ----------------
    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (t := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.control.set_target(t)
            await self.override.apply(self.control, self.sensors)
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.control.set_mode(hvac_mode)
        await self.override.apply(self.control, self.sensors)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.control.set_preset(preset_mode)
        await self.override.apply(self.control, self.sensors)
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Haupt-Update-Zyklus: Sensoren → Logik → Overrides."""
        try:
            await self.sensors.refresh()
            await self.control.evaluate(self.sensors)
            await self.override.apply(self.control, self.sensors)
        except Exception as e:
            _LOGGER.warning("Fehler im EcoThermostat-Update: %s", e)
        finally:
            self.async_write_ha_state()
