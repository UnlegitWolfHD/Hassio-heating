"""Climate platform for Eco Thermostat."""
import logging
from typing import Any, Optional

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    PRESET_ECO,
    PRESET_COMFORT,
    PRESET_SLEEP,
    PRESET_AWAY,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, CONF_NAME, CONF_HEATER, CONF_COOLER
from .sensors import SensorManager
from .control import ControlLogic

_LOGGER = logging.getLogger(__name__)

# Map internal preset names to HA constants
PRESET_MAP = {
    "eco": PRESET_ECO,
    "comfort": PRESET_COMFORT,
    "sleep": PRESET_SLEEP,
    "away": PRESET_AWAY,
}

REVERSE_PRESET_MAP = {v: k for k, v in PRESET_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eco Thermostat climate platform."""
    async_add_entities([EcoThermostatClimate(hass, entry)], True)


class EcoThermostatClimate(ClimateEntity):
    """Eco Thermostat climate entity."""

    _attr_should_poll = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the thermostat."""
        self.hass = hass
        self.entry = entry
        data = entry.data
        options = entry.options

        # Entity attributes
        self._attr_name = data[CONF_NAME]
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"

        # Initialize components
        self.sensors = SensorManager(hass, data, options)
        self.control = ControlLogic(
            hass,
            entry,
            data[CONF_HEATER],
            data.get(CONF_COOLER),
        )

        # HVAC modes
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        if data.get(CONF_COOLER):
            self._attr_hvac_modes.append(HVACMode.COOL)

        # Preset modes
        self._attr_preset_modes = [PRESET_ECO, PRESET_COMFORT, PRESET_SLEEP, PRESET_AWAY]

        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )

        self._enable_turn_on_off_backwards_compatibility = False

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self.sensors.current_temp

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the target temperature."""
        return self.control.target_temp

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        return self.control.hvac_mode

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        return self.control.hvac_action

    @property
    def preset_mode(self) -> Optional[str]:
        """Return current preset mode."""
        return PRESET_MAP.get(self.control.preset_mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.warning("Unsupported HVAC mode: %s", hvac_mode)
            return

        self.control.hvac_mode = hvac_mode
        await self.control.evaluate(self.sensors.current_temp)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in self._attr_preset_modes:
            _LOGGER.warning("Unsupported preset mode: %s", preset_mode)
            return

        # Convert HA preset to internal preset
        internal_preset = REVERSE_PRESET_MAP.get(preset_mode)
        if internal_preset:
            self.control.preset_mode = internal_preset
            self.control.target_temp = self.control.preset_temps[internal_preset]
            await self.control.evaluate(self.sensors.current_temp)
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if temperature := kwargs.get(ATTR_TEMPERATURE):
            self.control.target_temp = float(temperature)
            await self.control.evaluate(self.sensors.current_temp)
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Track window state changes
        if self.control.windows:

            async def _on_window_change(event):
                """Handle window state change."""
                await self.async_update()

            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self.control.windows, _on_window_change
                )
            )

    async def async_update(self) -> None:
        """Update the entity."""
        await self.sensors.update()
        await self.control.evaluate(self.sensors.current_temp)
        self.async_write_ha_state()
