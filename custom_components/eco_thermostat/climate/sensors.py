import logging

_LOGGER = logging.getLogger(__name__)


class SensorManager:
    def __init__(self, hass, data):
        self.hass = hass
        self.data = data

        # Entity IDs
        self.sensor_temp = data.get("sensor_temp")
        self.sensor_hum = data.get("sensor_humidity")

        # Optionen
        self.offset = float(data.get("temp_offset", 0.0))
        self.alpha = float(data.get("smoothing_alpha", 0.0))  # 0..1, 0 = aus

        # Werte
        self.current_temp = None
        self.smoothed_temp = None
        self.current_hum = None

    async def refresh(self):
        """Hole aktuelle Sensorwerte"""
        # Temperatur
        if self.sensor_temp:
            st = self.hass.states.get(self.sensor_temp)
            if st:
                try:
                    raw = float(st.state)
                    val = raw + self.offset

                    if self.alpha and 0.0 < self.alpha <= 1.0:
                        if self.smoothed_temp is None:
                            self.smoothed_temp = val
                        else:
                            self.smoothed_temp = (
                                self.alpha * val + (1.0 - self.alpha) * self.smoothed_temp
                            )
                        self.current_temp = self.smoothed_temp
                    else:
                        self.current_temp = val

                except (ValueError, TypeError):
                    _LOGGER.warning("Ungültiger Wert vom Temp-Sensor %s: %s", self.sensor_temp, st.state)

        # Luftfeuchtigkeit
        if self.sensor_hum:
            st_h = self.hass.states.get(self.sensor_hum)
            if st_h:
                try:
                    self.current_hum = float(st_h.state)
                except (ValueError, TypeError):
                    _LOGGER.warning("Ungültiger Wert vom Humidity-Sensor %s: %s", self.sensor_hum, st_h.state)
