"""Sensor management for Eco Thermostat."""
import logging
from typing import Optional
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class SensorManager:
    """Manage temperature and humidity sensors with offset and smoothing."""

    def __init__(self, hass: HomeAssistant, data: dict, options: dict) -> None:
        """Initialize sensor manager."""
        self.hass = hass
        self.sensor_temp = data.get("sensor_temp")
        self.sensor_hum = data.get("sensor_humidity")
        self.offset = float(data.get("temp_offset", 0.0))
        self.alpha = float(options.get("smoothing_alpha", 0.0))

        self.current_temp: Optional[float] = None
        self.current_hum: Optional[float] = None
        self._smoothed_temp: Optional[float] = None

    async def update(self) -> None:
        """Update sensor values."""
        await self._update_temperature()
        await self._update_humidity()

    async def _update_temperature(self) -> None:
        """Update temperature sensor."""
        if not self.sensor_temp:
            return

        state = self.hass.states.get(self.sensor_temp)
        if not state or state.state in ("unknown", "unavailable"):
            _LOGGER.debug("Temperature sensor %s unavailable", self.sensor_temp)
            return

        try:
            raw_temp = float(state.state)
            temp_with_offset = raw_temp + self.offset

            # Apply EMA smoothing if enabled
            if 0 < self.alpha <= 1.0:
                if self._smoothed_temp is None:
                    self._smoothed_temp = temp_with_offset
                else:
                    self._smoothed_temp = (
                        self.alpha * temp_with_offset +
                        (1 - self.alpha) * self._smoothed_temp
                    )
                self.current_temp = self._smoothed_temp
            else:
                self.current_temp = temp_with_offset

        except (ValueError, TypeError) as err:
            _LOGGER.warning("Invalid temperature value from %s: %s", self.sensor_temp, err)

    async def _update_humidity(self) -> None:
        """Update humidity sensor."""
        if not self.sensor_hum:
            return

        state = self.hass.states.get(self.sensor_hum)
        if not state or state.state in ("unknown", "unavailable"):
            return

        try:
            self.current_hum = float(state.state)
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Invalid humidity value from %s: %s", self.sensor_hum, err)
