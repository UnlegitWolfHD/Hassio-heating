import logging
from typing import Optional
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class SensorManager:
    """Verwaltet Temperatur- und Feuchtigkeitssensoren mit Offset und Glättung (EMA)."""

    def __init__(self, hass: HomeAssistant, data: dict) -> None:
        self.hass = hass
        self.data = data

        # Entity IDs
        self.sensor_temp: Optional[str] = data.get("sensor_temp")
        self.sensor_hum: Optional[str] = data.get("sensor_humidity")

        # Optionen
        self.offset: float = float(data.get("temp_offset", 0.0))
        self.alpha: float = float(data.get("smoothing_alpha", 0.0))  # 0..1, 0 = aus

        # Werte
        self.current_temp: Optional[float] = None
        self.smoothed_temp: Optional[float] = None
        self.current_hum: Optional[float] = None

    # -------------------------------------------------------------------------

    async def refresh(self) -> None:
        """Aktualisiert die Sensorwerte aus Home Assistant-States."""
        await self._update_temperature()
        await self._update_humidity()

    # -------------------------------------------------------------------------

    async def _update_temperature(self) -> None:
        """Temperatursensor lesen, Offset + Glättung anwenden."""
        if not self.sensor_temp:
            return

        state = self.hass.states.get(self.sensor_temp)
        if not state or state.state in ("unknown", "unavailable"):
            _LOGGER.debug("Temperatursensor %s nicht verfügbar (%s)", self.sensor_temp, state and state.state)
            return

        try:
            raw = float(state.state)
            val = raw + self.offset

            # Glättung (EMA)
            if 0.0 < self.alpha <= 1.0:
                if self.smoothed_temp is None:
                    self.smoothed_temp = val
                else:
                    self.smoothed_temp = self.alpha * val + (1.0 - self.alpha) * self.smoothed_temp
                self.current_temp = self.smoothed_temp
            else:
                self.current_temp = val

            _LOGGER.debug(
                "Temp-Update %s: Roh=%.2f, Offset=%.2f, Glättung=%.2f, Ergebnis=%.2f°C",
                self.sensor_temp,
                raw,
                self.offset,
                self.alpha,
                self.current_temp,
            )

        except (ValueError, TypeError):
            _LOGGER.warning("Ungültiger Wert vom Temp-Sensor %s: %s", self.sensor_temp, state.state)

    # -------------------------------------------------------------------------

    async def _update_humidity(self) -> None:
        """Luftfeuchtigkeitssensor lesen."""
        if not self.sensor_hum:
            return

        state = self.hass.states.get(self.sensor_hum)
        if not state or state.state in ("unknown", "unavailable"):
            _LOGGER.debug("Humidity-Sensor %s nicht verfügbar (%s)", self.sensor_hum, state and state.state)
            return

        try:
            self.current_hum = float(state.state)
            _LOGGER.debug("Humidity-Update %s: %.1f%%", self.sensor_hum, self.current_hum)
        except (ValueError, TypeError):
            _LOGGER.warning("Ungültiger Wert vom Humidity-Sensor %s: %s", self.sensor_hum, state.state)
