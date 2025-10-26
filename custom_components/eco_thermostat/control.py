"""Control logic for Eco Thermostat."""
import time
import logging
from typing import Optional
from homeassistant.components.climate.const import HVACMode, HVACAction

_LOGGER = logging.getLogger(__name__)


class ControlLogic:
    """Control logic for heating/cooling with deadband and anti-short-cycling."""

    def __init__(self, hass, entry, heater_entity: str, cooler_entity: Optional[str]):
        """Initialize control logic."""
        self.hass = hass
        self.entry = entry
        self.heater_entity = heater_entity
        self.cooler_entity = cooler_entity

        # Get options
        options = entry.options

        # Preset temperatures
        self.preset_temps = {
            "eco": float(options.get("preset_eco", 18.0)),
            "comfort": float(options.get("preset_comfort", 22.0)),
            "sleep": float(options.get("preset_sleep", 19.0)),
            "away": float(options.get("preset_away", 16.0)),
        }

        # Current state
        self.hvac_mode = HVACMode.HEAT
        self.hvac_action = HVACAction.IDLE
        self.preset_mode = "comfort"
        self.target_temp = self.preset_temps["comfort"]

        # Control parameters
        self.deadband = float(options.get("deadband", 0.5))
        self.frost_temp = float(options.get("frost_temp", 5.0))
        self.window_mode = options.get("window_mode", "frost")
        self.min_run = int(options.get("min_run_seconds", 180))
        self.min_idle = int(options.get("min_idle_seconds", 180))

        # Window sensors
        data = entry.data
        self.windows = data.get("windows", [])

        # Internal state
        self._last_change = 0.0
        self._is_heating = False
        self._is_cooling = False
        self._window_was_open = False
        self._saved_before_window: Optional[tuple] = None

    def _is_window_open(self) -> bool:
        """Check if any window is open."""
        if not self.windows:
            return False

        for window_entity in self.windows:
            state = self.hass.states.get(window_entity)
            if state and state.state == "on":
                return True
        return False

    async def evaluate(self, current_temp: Optional[float]) -> None:
        """Evaluate and control heating/cooling."""
        if current_temp is None:
            self.hvac_action = HVACAction.IDLE
            await self._turn_off_all()
            return

        # Handle window logic
        window_open = self._is_window_open()

        if window_open:
            if not self._window_was_open:
                # Window just opened - save current state
                self._saved_before_window = (self.hvac_mode, self.target_temp)
                self._window_was_open = True
                _LOGGER.info("Window opened - applying window mode: %s", self.window_mode)

            if self.window_mode == "off":
                # Turn everything off
                self.hvac_action = HVACAction.OFF
                await self._turn_off_all()
                return
            else:
                # Frost protection mode
                saved_hvac = self.hvac_mode
                saved_target = self.target_temp
                self.hvac_mode = HVACMode.HEAT
                self.target_temp = self.frost_temp
                await self._control_heating(current_temp)
                # Don't restore yet - keep frost mode active
                return

        if self._window_was_open and not window_open:
            # Window just closed - restore previous state
            self._window_was_open = False
            if self._saved_before_window:
                self.hvac_mode, self.target_temp = self._saved_before_window
                self._saved_before_window = None
                _LOGGER.info("Window closed - restoring previous mode")

        # Normal operation
        if self.hvac_mode == HVACMode.OFF:
            self.hvac_action = HVACAction.OFF
            await self._turn_off_all()
        elif self.hvac_mode == HVACMode.HEAT:
            await self._control_heating(current_temp)
        elif self.hvac_mode == HVACMode.COOL:
            await self._control_cooling(current_temp)

    async def _control_heating(self, current_temp: float) -> None:
        """Control heating with hysteresis and anti-short-cycling."""
        now = time.time()
        target_low = self.target_temp - self.deadband
        target_high = self.target_temp + self.deadband

        if current_temp < target_low:
            # Need heating
            if not self._is_heating:
                # Check min idle time
                if self._last_change > 0 and (now - self._last_change) < self.min_idle:
                    _LOGGER.debug(
                        "Anti-short-cycling: waiting %.0fs more",
                        self.min_idle - (now - self._last_change)
                    )
                    self.hvac_action = HVACAction.IDLE
                    return

                # Turn on heater
                await self._turn_on_heater()
                self._is_heating = True
                self._last_change = now
                self.hvac_action = HVACAction.HEATING
                _LOGGER.info("Heater ON: %.1f°C < %.1f°C", current_temp, target_low)
            else:
                self.hvac_action = HVACAction.HEATING

        elif current_temp > target_high:
            # Don't need heating
            if self._is_heating:
                # Check min run time
                if (now - self._last_change) < self.min_run:
                    _LOGGER.debug(
                        "Min run time: heater running %.0fs more",
                        self.min_run - (now - self._last_change)
                    )
                    self.hvac_action = HVACAction.HEATING
                    return

                # Turn off heater
                await self._turn_off_heater()
                self._is_heating = False
                self._last_change = now
                self.hvac_action = HVACAction.IDLE
                _LOGGER.info("Heater OFF: %.1f°C > %.1f°C", current_temp, target_high)
            else:
                self.hvac_action = HVACAction.IDLE
        else:
            # In deadband - maintain current state
            self.hvac_action = HVACAction.HEATING if self._is_heating else HVACAction.IDLE

    async def _control_cooling(self, current_temp: float) -> None:
        """Control cooling with hysteresis and anti-short-cycling."""
        now = time.time()
        target_low = self.target_temp - self.deadband
        target_high = self.target_temp + self.deadband

        if current_temp > target_high:
            # Need cooling
            if not self._is_cooling:
                # Check min idle time
                if self._last_change > 0 and (now - self._last_change) < self.min_idle:
                    _LOGGER.debug(
                        "Anti-short-cycling: waiting %.0fs more",
                        self.min_idle - (now - self._last_change)
                    )
                    self.hvac_action = HVACAction.IDLE
                    return

                # Turn on cooler
                await self._turn_on_cooler()
                self._is_cooling = True
                self._last_change = now
                self.hvac_action = HVACAction.COOLING
                _LOGGER.info("Cooler ON: %.1f°C > %.1f°C", current_temp, target_high)
            else:
                self.hvac_action = HVACAction.COOLING

        elif current_temp < target_low:
            # Don't need cooling
            if self._is_cooling:
                # Check min run time
                if (now - self._last_change) < self.min_run:
                    _LOGGER.debug(
                        "Min run time: cooler running %.0fs more",
                        self.min_run - (now - self._last_change)
                    )
                    self.hvac_action = HVACAction.COOLING
                    return

                # Turn off cooler
                await self._turn_off_cooler()
                self._is_cooling = False
                self._last_change = now
                self.hvac_action = HVACAction.IDLE
                _LOGGER.info("Cooler OFF: %.1f°C < %.1f°C", current_temp, target_low)
            else:
                self.hvac_action = HVACAction.IDLE
        else:
            # In deadband - maintain current state
            self.hvac_action = HVACAction.COOLING if self._is_cooling else HVACAction.IDLE

    async def _turn_on_heater(self) -> None:
        """Turn on the heater."""
        if self.heater_entity:
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {"entity_id": self.heater_entity, "hvac_mode": "heat"},
                    blocking=False,
                )
            except Exception as err:
                _LOGGER.error("Failed to turn on heater: %s", err)

    async def _turn_off_heater(self) -> None:
        """Turn off the heater."""
        if self.heater_entity:
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {"entity_id": self.heater_entity, "hvac_mode": "off"},
                    blocking=False,
                )
            except Exception as err:
                _LOGGER.error("Failed to turn off heater: %s", err)

    async def _turn_on_cooler(self) -> None:
        """Turn on the cooler."""
        if self.cooler_entity:
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {"entity_id": self.cooler_entity, "hvac_mode": "cool"},
                    blocking=False,
                )
            except Exception as err:
                _LOGGER.error("Failed to turn on cooler: %s", err)

    async def _turn_off_cooler(self) -> None:
        """Turn off the cooler."""
        if self.cooler_entity:
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {"entity_id": self.cooler_entity, "hvac_mode": "off"},
                    blocking=False,
                )
            except Exception as err:
                _LOGGER.error("Failed to turn off cooler: %s", err)

    async def _turn_off_all(self) -> None:
        """Turn off all devices."""
        await self._turn_off_heater()
        await self._turn_off_cooler()
        self._is_heating = False
        self._is_cooling = False
