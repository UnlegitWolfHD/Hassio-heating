import logging
from typing import Optional
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class SensorManager:
    """Verwaltet Temperatur- und Feuchtigkeitssensoren mit Offset & Glättung."""

    def __init__(self, hass: HomeAssistant, data: dict) -> None:
        self.hass = hass
        self.sensor_temp = data.get("sensor_temp")
        self.sensor_hum = data.get("sensor_humidity")
        self.offset = float(data.get("temp_offset", 0.0))
        self.alpha = float(data.get("smoothing_alpha", 0.0))
        self.current_temp: Optional[float] = None
        self.current_hum: Optional[float] = None
        self.smoothed_temp: Optional[float] = None

    async def refresh(self) -> None:
        """Aktualisiert Sensorwerte."""
        await self._update_temp()
        await self._update_hum()

    async def _update_temp(self):
        if not self.sensor_temp:
            return
        st = self.hass.states.get(self.sensor_temp)
        if not st or st.state in ("unknown", "unavailable"):
            _LOGGER.debug("Temperatursensor %s nicht verfügbar", self.sensor_temp)
            return
        try:
            raw = float(st.state)
            val = raw + self.offset
            if 0 < self.alpha <= 1.0:
                self.smoothed_temp = val if self.smoothed_temp is None else self.alpha * val + (1 - self.alpha) * self.smoothed_temp
                self.current_temp = self.smoothed_temp
            else:
                self.current_temp = val
        except (ValueError, TypeError):
            _LOGGER.warning("Ungültiger Wert von %s: %s", self.sensor_temp, st.state)

    async def _update_hum(self):
        if not self.sensor_hum:
            return
        st = self.hass.states.get(self.sensor_hum)
        if not st or st.state in ("unknown", "unavailable"):
            return
        try:
            self.current_hum = float(st.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Ungültiger Wert von %s: %s", self.sensor_hum, st.state)
