import time
import logging
from typing import Optional
from homeassistant.components.climate.const import HVACMode

_LOGGER = logging.getLogger(__name__)

class ControlLogic:
    """Kernlogik der Heiz-/Kühlregelung."""

    def __init__(self, hass, entry, heater, cooler):
        self.hass = hass
        self.entry = entry
        self.heater = heater
        self.cooler = cooler

        opts = entry.options or {}
        data = entry.data or {}
        self.presets = opts.get("presets", {})
        self.target_temp = float(self.presets.get("comfort", 22))
        self.preset_mode = "comfort"
        self.hvac_mode = HVACMode.HEAT

        self.deadband = float(opts.get("deadband", 0.4))
        self.frost_temp = float(opts.get("frost_temp", 5.0))
        self.window_mode = opts.get("window_mode", "frost")
        self.min_run = int(opts.get("min_run_seconds", 180))
        self.min_idle = int(opts.get("min_idle_seconds", 180))
        self.windows = data.get("windows", [])
        self._last_change = 0.0
        self._saved_before_window: Optional[tuple[HVACMode, float]] = None
        self._window_was_open = False

    def _window_open(self) -> bool:
        for w in self.windows:
            st = self.hass.states.get(w)
            if st and st.state == "on":
                return True
        return False

    async def evaluate(self, sensors):
        ct = sensors.current_temp
        if ct is None:
            return
        win_open = self._window_open()
        if win_open:
            if not self._window_was_open:
                self._saved_before_window = (self.hvac_mode, self.target_temp)
                self._window_was_open = True
            if self.window_mode == "off":
                self.hvac_mode = HVACMode.OFF
            else:
                self.hvac_mode = HVACMode.HEAT
                self.target_temp = self.frost_temp
            return
        if self._window_was_open and not win_open:
            self._window_was_open = False
            if self._saved_before_window:
                self.hvac_mode, self.target_temp = self._saved_before_window
                self._saved_before_window = None
        # Regelung
        if self.hvac_mode == HVACMode.HEAT and ct < self.target_temp - self.deadband:
            _LOGGER.debug("Heizung EIN: %.1f < %.1f", ct, self.target_temp)
        elif self.hvac_mode == HVACMode.HEAT and ct > self.target_temp + self.deadband:
            _LOGGER.debug("Heizung AUS: %.1f > %.1f", ct, self.target_temp)
