import time
import logging
from homeassistant.components.climate.const import HVACMode

_LOGGER = logging.getLogger(__name__)


class ControlLogic:
    def __init__(self, hass, entry, heater, cooler):
        self.hass = hass
        self.entry = entry
        self.heater = heater
        self.cooler = cooler

        opts = entry.options or {}

        self.presets = opts.get("presets", {"eco": 18, "comfort": 22, "sleep": 19, "away": 16})
        self.hvac_mode = HVACMode.HEAT
        self.target_temp = float(self.presets.get("comfort", 22))
        self.preset_mode = "comfort"

        # Optionen
        self.deadband = float(opts.get("deadband", 0.4))
        self.window_mode = opts.get("window_mode", "frost")  # "off" | "frost"
        self.frost_temp = float(opts.get("frost_temp", 5.0))
        self.min_run = int(opts.get("min_run_seconds", 180))
        self.min_idle = int(opts.get("min_idle_seconds", 180))
        self.windows = entry.data.get("windows", [])

        # interner State
        self._last_state_change = 0.0
        self._saved_before_window = None

    def supported_modes(self, cooler):
        return [HVACMode.OFF, HVACMode.HEAT] + ([HVACMode.COOL, HVACMode.AUTO] if cooler else [])

    async def set_target(self, t: float):
        self.target_temp = float(t)

    async def set_mode(self, mode: HVACMode):
        self.hvac_mode = mode

    async def set_preset(self, preset: str):
        if preset in self.presets:
            self.preset_mode = preset
            self.target_temp = float(self.presets[preset])

    def _window_open(self):
        """Prüfen, ob einer der Fensterkontakte offen ist"""
        for w in self.windows:
            st = self.hass.states.get(w)
            if st and st.state == "on":
                return True
        return False

    def _respect_min_times(self, hvac_action: str) -> bool:
        now = time.time()
        elapsed = now - self._last_state_change
        if hvac_action in ("heating", "cooling"):
            return elapsed >= self.min_run
        else:
            return elapsed >= self.min_idle

    async def evaluate(self, sensors):
        """Hauptlogik, entscheidet HVAC-Mode anhand Sensorwerten"""
        ct = sensors.current_temp
        if ct is None:
            return

        # Fenster offen?
        if self._window_open():
            if self._saved_before_window is None:
                self._saved_before_window = (self.hvac_mode, self.target_temp)
            if self.window_mode == "off":
                self.hvac_mode = HVACMode.OFF
            else:  # frost
                self.hvac_mode = HVACMode.HEAT
                self.target_temp = self.frost_temp
            _LOGGER.debug("Fenster offen: Mode=%s, Target=%.1f", self.hvac_mode, self.target_temp)
            return
        else:
            if self._saved_before_window:
                prev_mode, prev_temp = self._saved_before_window
                self.hvac_mode, self.target_temp = prev_mode, prev_temp
                self._saved_before_window = None

        # Auto-Modus
        if self.hvac_mode == HVACMode.AUTO and self.cooler:
            if ct < self.target_temp - self.deadband:
                self.hvac_mode = HVACMode.HEAT
                self._last_state_change = time.time()
            elif ct > self.target_temp + self.deadband:
                self.hvac_mode = HVACMode.COOL
                self._last_state_change = time.time()
            return

        # Heat / Cool mit Deadband
        if self.hvac_mode == HVACMode.HEAT:
            if ct < self.target_temp - self.deadband:
                if self._respect_min_times("heating"):
                    _LOGGER.debug("Heizung EIN bei %.1f < %.1f", ct, self.target_temp)
                    self._last_state_change = time.time()
            elif ct > self.target_temp + self.deadband:
                if self._respect_min_times("idle"):
                    _LOGGER.debug("Heizung AUS bei %.1f > %.1f", ct, self.target_temp)
                    self._last_state_change = time.time()

        if self.hvac_mode == HVACMode.COOL:
            if ct > self.target_temp + self.deadband:
                if self._respect_min_times("cooling"):
                    _LOGGER.debug("Kühlung EIN bei %.1f > %.1f", ct, self.target_temp)
                    self._last_state_change = time.time()
            elif ct < self.target_temp - self.deadband:
                if self._respect_min_times("idle"):
                    _LOGGER.debug("Kühlung AUS bei %.1f < %.1f", ct, self.target_temp)
                    self._last_state_change = time.time()
