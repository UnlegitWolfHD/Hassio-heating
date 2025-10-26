import time
import logging
from typing import Optional
from homeassistant.components.climate.const import HVACMode, HVACAction

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
        self.presets = opts.get("presets", {
            "comfort": 22.0,
            "eco": 18.0,
            "sleep": 19.0,
            "away": 16.0
        })
        self.target_temp = float(self.presets.get("comfort", 22))
        self.preset_mode = "comfort"
        self.hvac_mode = HVACMode.HEAT
        self.hvac_action = HVACAction.IDLE

        self.deadband = float(opts.get("deadband", 0.4))
        self.frost_temp = float(opts.get("frost_temp", 5.0))
        self.window_mode = opts.get("window_mode", "frost")
        self.min_run = int(opts.get("min_run_seconds", 180))
        self.min_idle = int(opts.get("min_idle_seconds", 180))
        self.windows = data.get("windows", [])
        self._last_change = 0.0
        self._saved_before_window: Optional[tuple[HVACMode, float]] = None
        self._window_was_open = False
        self._is_heating = False
        self._is_cooling = False

    def _window_open(self) -> bool:
        for w in self.windows:
            st = self.hass.states.get(w)
            if st and st.state == "on":
                return True
        return False

    async def evaluate(self, sensors):
        ct = sensors.current_temp
        if ct is None:
            self.hvac_action = HVACAction.IDLE
            await self._turn_off_all()
            return

        # Fensterlogik
        win_open = self._window_open()
        if win_open:
            if not self._window_was_open:
                self._saved_before_window = (self.hvac_mode, self.target_temp)
                self._window_was_open = True
            if self.window_mode == "off":
                self.hvac_mode = HVACMode.OFF
                self.hvac_action = HVACAction.OFF
                await self._turn_off_all()
            else:
                self.hvac_mode = HVACMode.HEAT
                self.target_temp = self.frost_temp
                await self._control_heating(ct)
            return

        if self._window_was_open and not win_open:
            self._window_was_open = False
            if self._saved_before_window:
                self.hvac_mode, self.target_temp = self._saved_before_window
                self._saved_before_window = None

        # Normale Regelung
        if self.hvac_mode == HVACMode.OFF:
            self.hvac_action = HVACAction.OFF
            await self._turn_off_all()
        elif self.hvac_mode == HVACMode.HEAT:
            await self._control_heating(ct)
        elif self.hvac_mode == HVACMode.COOL:
            await self._control_cooling(ct)

    async def _control_heating(self, current_temp: float):
        """Steuert die Heizung mit Hysterese und Anti-Short-Cycling."""
        now = time.time()

        if current_temp < self.target_temp - self.deadband:
            # Heizen erforderlich
            if not self._is_heating:
                # Prüfe min_idle
                if self._last_change > 0 and (now - self._last_change) < self.min_idle:
                    _LOGGER.debug("Anti-Short-Cycling: Warte noch %.0fs", self.min_idle - (now - self._last_change))
                    self.hvac_action = HVACAction.IDLE
                    return
                # Heizung einschalten
                await self._turn_on_heater()
                self._is_heating = True
                self._last_change = now
                self.hvac_action = HVACAction.HEATING
                _LOGGER.info("Heizung EIN: %.1f°C < %.1f°C", current_temp, self.target_temp - self.deadband)
            else:
                self.hvac_action = HVACAction.HEATING
        elif current_temp > self.target_temp + self.deadband:
            # Heizen nicht mehr erforderlich
            if self._is_heating:
                # Prüfe min_run
                if (now - self._last_change) < self.min_run:
                    _LOGGER.debug("Min-Run: Heizung läuft noch %.0fs", self.min_run - (now - self._last_change))
                    self.hvac_action = HVACAction.HEATING
                    return
                # Heizung ausschalten
                await self._turn_off_heater()
                self._is_heating = False
                self._last_change = now
                self.hvac_action = HVACAction.IDLE
                _LOGGER.info("Heizung AUS: %.1f°C > %.1f°C", current_temp, self.target_temp + self.deadband)
            else:
                self.hvac_action = HVACAction.IDLE
        else:
            # In der Deadband-Zone
            self.hvac_action = HVACAction.HEATING if self._is_heating else HVACAction.IDLE

    async def _control_cooling(self, current_temp: float):
        """Steuert die Kühlung mit Hysterese und Anti-Short-Cycling."""
        now = time.time()

        if current_temp > self.target_temp + self.deadband:
            # Kühlen erforderlich
            if not self._is_cooling:
                # Prüfe min_idle
                if self._last_change > 0 and (now - self._last_change) < self.min_idle:
                    _LOGGER.debug("Anti-Short-Cycling: Warte noch %.0fs", self.min_idle - (now - self._last_change))
                    self.hvac_action = HVACAction.IDLE
                    return
                # Kühlung einschalten
                await self._turn_on_cooler()
                self._is_cooling = True
                self._last_change = now
                self.hvac_action = HVACAction.COOLING
                _LOGGER.info("Kühlung EIN: %.1f°C > %.1f°C", current_temp, self.target_temp + self.deadband)
            else:
                self.hvac_action = HVACAction.COOLING
        elif current_temp < self.target_temp - self.deadband:
            # Kühlen nicht mehr erforderlich
            if self._is_cooling:
                # Prüfe min_run
                if (now - self._last_change) < self.min_run:
                    _LOGGER.debug("Min-Run: Kühlung läuft noch %.0fs", self.min_run - (now - self._last_change))
                    self.hvac_action = HVACAction.COOLING
                    return
                # Kühlung ausschalten
                await self._turn_off_cooler()
                self._is_cooling = False
                self._last_change = now
                self.hvac_action = HVACAction.IDLE
                _LOGGER.info("Kühlung AUS: %.1f°C < %.1f°C", current_temp, self.target_temp - self.deadband)
            else:
                self.hvac_action = HVACAction.IDLE
        else:
            # In der Deadband-Zone
            self.hvac_action = HVACAction.COOLING if self._is_cooling else HVACAction.IDLE

    async def _turn_on_heater(self):
        """Schaltet die Heizung ein."""
        if self.heater:
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": self.heater, "hvac_mode": HVACMode.HEAT},
                blocking=False
            )

    async def _turn_off_heater(self):
        """Schaltet die Heizung aus."""
        if self.heater:
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": self.heater, "hvac_mode": HVACMode.OFF},
                blocking=False
            )

    async def _turn_on_cooler(self):
        """Schaltet die Kühlung ein."""
        if self.cooler:
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": self.cooler, "hvac_mode": HVACMode.COOL},
                blocking=False
            )

    async def _turn_off_cooler(self):
        """Schaltet die Kühlung aus."""
        if self.cooler:
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": self.cooler, "hvac_mode": HVACMode.OFF},
                blocking=False
            )

    async def _turn_off_all(self):
        """Schaltet alle Geräte aus."""
        await self._turn_off_heater()
        await self._turn_off_cooler()
        self._is_heating = False
        self._is_cooling = False
