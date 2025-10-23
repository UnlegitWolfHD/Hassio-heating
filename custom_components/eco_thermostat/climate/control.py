import time
import logging
from typing import Any, Optional
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.climate.const import HVACMode

_LOGGER = logging.getLogger(__name__)


class ControlLogic:
    """Kernlogik des Eco Thermostat – Steuerung basierend auf Sensorwerten und Optionen."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, heater: str, cooler: Optional[str]):
        self.hass = hass
        self.entry = entry
        self.heater = heater
        self.cooler = cooler

        opts = entry.options or {}
        data = entry.data or {}

        # Presets und Zieltemperaturen
        self.presets: dict[str, float] = opts.get(
            "presets",
            {"eco": 18.0, "comfort": 22.0, "sleep": 19.0, "away": 16.0}
        )
        self.preset_mode: str = "comfort"
        self.target_temp: float = float(self.presets.get(self.preset_mode, 22.0))
        self.hvac_mode: HVACMode = HVACMode.HEAT

        # Optionen
        self.deadband: float = float(opts.get("deadband", 0.4))
        self.window_mode: str = opts.get("window_mode", "frost")  # "off" | "frost"
        self.frost_temp: float = float(opts.get("frost_temp", 5.0))
        self.min_run: int = int(opts.get("min_run_seconds", 180))
        self.min_idle: int = int(opts.get("min_idle_seconds", 180))
        self.windows: list[str] = data.get("windows", [])

        # Interner State
        self._last_state_change: float = 0.0
        self._saved_before_window: Optional[tuple[HVACMode, float]] = None
        self._active: bool = False  # ob Heizung/Kühlung aktuell an ist

    # -------------------------------------------------------------------------

    def supported_modes(self) -> list[HVACMode]:
        """Liefert unterstützte Modi abhängig vom Vorhandensein eines Coolers."""
        modes = [HVACMode.OFF, HVACMode.HEAT]
        if self.cooler:
            modes += [HVACMode.COOL, HVACMode.AUTO]
        return modes

    # -------------------------------------------------------------------------

    async def set_target(self, temperature: float) -> None:
        self.target_temp = float(temperature)
        _LOGGER.debug("Neue Solltemperatur: %.1f°C", self.target_temp)

    async def set_mode(self, mode: HVACMode) -> None:
        self.hvac_mode = mode
        _LOGGER.debug("Modus gesetzt: %s", mode)

    async def set_preset(self, preset: str) -> None:
        if preset in self.presets:
            self.preset_mode = preset
            self.target_temp = float(self.presets[preset])
            _LOGGER.debug("Preset gewechselt: %s → %.1f°C", preset, self.target_temp)

    # -------------------------------------------------------------------------

    def _window_open(self) -> bool:
        """Prüfen, ob einer der Fensterkontakte offen ist."""
        for entity_id in self.windows:
            state = self.hass.states.get(entity_id)
            if state and state.state == "on":
                return True
        return False

    def _respect_min_times(self, turning_on: bool) -> bool:
        """Verhindert zu häufiges Schalten."""
        now = time.time()
        elapsed = now - self._last_state_change
        required = self.min_idle if turning_on else self.min_run
        return elapsed >= required

    # -------------------------------------------------------------------------

    async def evaluate(self, sensors: Any) -> None:
        """Hauptlogik: entscheidet Heiz-/Kühlverhalten anhand aktueller Werte."""
        current_temp = getattr(sensors, "current_temp", None)
        if current_temp is None:
            _LOGGER.debug("Kein Temperaturwert verfügbar – Abbruch.")
            return

        # --- Fenster geöffnet ---
        if self._window_open():
            await self._handle_window_open()
            return
        else:
            await self._restore_after_window()

        # --- Automatikmodus ---
        if self.hvac_mode == HVACMode.AUTO and self.cooler:
            await self._handle_auto_mode(current_temp)
            return

        # --- Heizen / Kühlen ---
        if self.hvac_mode == HVACMode.HEAT:
            await self._handle_heat(current_temp)
        elif self.hvac_mode == HVACMode.COOL:
            await self._handle_cool(current_temp)

    # -------------------------------------------------------------------------

    async def _handle_window_open(self) -> None:
        """Reaktion auf geöffnete Fenster."""
        if self._saved_before_window is None:
            self._saved_before_window = (self.hvac_mode, self.target_temp)

        if self.window_mode == "off":
            self.hvac_mode = HVACMode.OFF
        else:
            self.hvac_mode = HVACMode.HEAT
            self.target_temp = self.frost_temp

        _LOGGER.debug("Fenster offen – wechsle in %s bei %.1f°C", self.hvac_mode, self.target_temp)

    async def _restore_after_window(self) -> None:
        """Zustand nach Schließen des Fensters wiederherstellen."""
        if self._saved_before_window:
            self.hvac_mode, self.target_temp = self._saved_before_window
            self._saved_before_window = None
            _LOGGER.debug("Fenster geschlossen – vorheriger Zustand wiederhergestellt: %s, %.1f°C",
                          self.hvac_mode, self.target_temp)

    async def _handle_auto_mode(self, current_temp: float) -> None:
        """Automatischer Wechsel zwischen Heizen/Kühlen."""
        if current_temp < self.target_temp - self.deadband:
            self.hvac_mode = HVACMode.HEAT
        elif current_temp > self.target_temp + self.deadband:
            self.hvac_mode = HVACMode.COOL
        _LOGGER.debug("Auto-Mode aktiv: Temp=%.1f°C, Mode=%s", current_temp, self.hvac_mode)
        self._last_state_change = time.time()

    async def _handle_heat(self, current_temp: float) -> None:
        """Heizlogik."""
        if current_temp < self.target_temp - self.deadband:
            if not self._active and self._respect_min_times(turning_on=True):
                self._set_active(True, "Heizung EIN")
        elif current_temp > self.target_temp + self.deadband:
            if self._active and self._respect_min_times(turning_on=False):
                self._set_active(False, "Heizung AUS")

    async def _handle_cool(self, current_temp: float) -> None:
        """Kühllogik."""
        if current_temp > self.target_temp + self.deadband:
            if not self._active and self._respect_min_times(turning_on=True):
                self._set_active(True, "Kühlung EIN")
        elif current_temp < self.target_temp - self.deadband:
            if self._active and self._respect_min_times(turning_on=False):
                self._set_active(False, "Kühlung AUS")

    def _set_active(self, active: bool, msg: str) -> None:
        self._active = active
        self._last_state_change = time.time()
        _LOGGER.debug("%s – aktuelle Temp %.1f°C, Soll %.1f°C", msg, self.target_temp, self.target_temp)
