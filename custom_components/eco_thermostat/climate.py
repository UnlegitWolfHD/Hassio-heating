from __future__ import annotations
import logging, time
from typing import Any, Optional, List

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature

from .const import (
    CONF_NAME, CONF_HEATER, CONF_COOLER, CONF_SENSOR, CONF_TEMP_OFFSET, CONF_WINDOWS,
    CONF_DEADBAND, CONF_MIN_RUN_SECONDS, CONF_MIN_IDLE_SECONDS, CONF_WINDOW_MODE,
    CONF_FROST_TEMP, CONF_SMOOTHING_ALPHA, CONF_PRESETS, DEFAULT_PRESETS, DOMAIN
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = 30.0  # seconds

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    entity = EcoThermostatEntity(hass, entry)
    async_add_entities([entity])


class EcoThermostatEntity(ClimateEntity):
    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry

        data = entry.data

        self._name: str = data[CONF_NAME]
        self._heater: str = data[CONF_HEATER]
        self._cooler: Optional[str] = data.get(CONF_COOLER)
        self._sensor: str = data[CONF_SENSOR]
        self._windows: List[str] = data.get(CONF_WINDOWS, [])
        self._offset: float = float(data.get(CONF_TEMP_OFFSET, 0.0))

        # Options
        opts = entry.options or {}
        self._deadband: float = float(opts.get(CONF_DEADBAND, 0.4))
        self._min_run: int = int(opts.get(CONF_MIN_RUN_SECONDS, 180))
        self._min_idle: int = int(opts.get(CONF_MIN_IDLE_SECONDS, 180))
        self._window_mode: str = opts.get(CONF_WINDOW_MODE, "frost")
        self._frost_temp: float = float(opts.get(CONF_FROST_TEMP, 5.0))
        self._alpha: float = float(opts.get(CONF_SMOOTHING_ALPHA, 0.0))
        self._presets = opts.get(CONF_PRESETS, DEFAULT_PRESETS)

        # State
        self._attr_name = self._name
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT] + ([HVACMode.COOL, HVACMode.AUTO] if self._cooler else [])
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_preset_modes = list(self._presets.keys())

        self._current_temp: Optional[float] = None
        self._smoothed_temp: Optional[float] = None
        self._attr_target_temperature: float = float(self._presets.get("comfort", 22.0))
        self._attr_hvac_mode: HVACMode = HVACMode.HEAT
        self._attr_preset_mode: str = "comfort"

        self._last_state_change_ts: float = 0.0
        self._last_command_ts: float = 0.0
        self._saved_before_window = None  # (hvac_mode, target)

        self._unsub_sensor = None
        self._unsub_windows = []
        self._unsub_timer = None

    async def async_added_to_hass(self) -> None:
        # subscribe sensor updates
        self._unsub_sensor = async_track_state_change_event(
            self.hass, [self._sensor], self._handle_sensor_change
        )
        # subscribe window contacts
        if self._windows:
            self._unsub_windows = [
                async_track_state_change_event(self.hass, [w], self._handle_window_change)
                for w in self._windows
            ]
        # periodic re-eval
        self._schedule_tick()
        # set initial current temp
        self._refresh_temperature()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_sensor:
            self._unsub_sensor()
        for u in self._unsub_windows:
            u()
        if self._unsub_timer:
            self._unsub_timer()

    @property
    def current_temperature(self) -> Optional[float]:
        return self._smoothed_temp if self._alpha and self._smoothed_temp is not None else self._current_temp

    @property
    def hvac_action(self):
        # Optional: indicate action (heating/cooling/idle)
        if self._attr_hvac_mode == HVACMode.OFF:
            return None
        ct = self.current_temperature
        if ct is None:
            return None
        if self._attr_hvac_mode == HVACMode.HEAT and ct < self._attr_target_temperature - self._deadband:
            return "heating"
        if self._attr_hvac_mode == HVACMode.COOL and ct > self._attr_target_temperature + self._deadband:
            return "cooling"
        return "idle"

    # Handlers
    def _schedule_tick(self):
        self._unsub_timer = async_call_later(self.hass, UPDATE_INTERVAL, self._on_tick)

    async def _on_tick(self, _now):
        self._refresh_temperature()
        self._evaluate_control()
        self.async_write_ha_state()
        self._schedule_tick()

    @callback
    def _handle_sensor_change(self, event):
        self._refresh_temperature()
        self._evaluate_control()
        self.async_write_ha_state()

    @callback
    def _handle_window_change(self, event):
        self._evaluate_control(force=True)
        self.async_write_ha_state()

    def _refresh_temperature(self):
        st = self.hass.states.get(self._sensor)
        if not st:
            return
        try:
            raw = float(st.state)
        except (ValueError, TypeError):
            return
        val = raw + self._offset
        if self._alpha and self._alpha > 0.0 and self._alpha <= 1.0:
            if self._smoothed_temp is None:
                self._smoothed_temp = val
            else:
                self._smoothed_temp = self._alpha * val + (1.0 - self._alpha) * self._smoothed_temp
        self._current_temp = val

    # Climate API
    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (t := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        self._attr_target_temperature = float(t)
        await self._apply_target()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._attr_hvac_mode = hvac_mode
        await self._apply_target()
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in self._presets:
            return
        self._attr_preset_mode = preset_mode
        self._attr_target_temperature = float(self._presets[preset_mode])
        await self._apply_target()
        self.async_write_ha_state()

    # Control logic
    def _window_open(self) -> bool:
        for w in self._windows:
            st = self.hass.states.get(w)
            if st and st.state == "on":
                return True
        return False

    def _respect_min_times(self) -> bool:
        now = time.time()
        elapsed = now - self._last_state_change_ts
        if self.hvac_action in ("heating", "cooling"):
            return elapsed >= self._min_run
        else:
            return elapsed >= self._min_idle

    def _evaluate_control(self, force: bool = False):
        ct = self.current_temperature
        if ct is None:
            return

        # Window logic
        if self._window_open():
            if self._saved_before_window is None:
                self._saved_before_window = (self._attr_hvac_mode, self._attr_target_temperature)
            if self._window_mode == "off":
                self._attr_hvac_mode = HVACMode.OFF
            else:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_target_temperature = self._frost_temp
            self.hass.async_create_task(self._apply_target(push_immediately=True))
            return
        else:
            if self._saved_before_window is not None:
                prev_mode, prev_target = self._saved_before_window
                self._saved_before_window = None
                self._attr_hvac_mode = prev_mode
                self._attr_target_temperature = prev_target

        # AUTO decision if cooler available
        if self._attr_hvac_mode == HVACMode.AUTO and self._cooler:
            next_mode = None
            if ct < self._attr_target_temperature - self._deadband:
                next_mode = HVACMode.HEAT
            elif ct > self._attr_target_temperature + self._deadband:
                next_mode = HVACMode.COOL

            if next_mode and (force or self._respect_min_times()):
                self._attr_hvac_mode = next_mode
                self._last_state_change_ts = time.time()
                self.hass.async_create_task(self._apply_target(push_immediately=True))
            return

        # In explicit HEAT/COOL: just push (respect min times)
        if self._attr_hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            if not (force or self._respect_min_times()):
                return
            self.hass.async_create_task(self._apply_target(push_immediately=True))

    async def _apply_target(self, push_immediately: bool = False):
        now = time.time()
        if not push_immediately and (now - self._last_command_ts) < 1.0:
            return

        # OFF: power down both
        if self._attr_hvac_mode == HVACMode.OFF:
            if self._heater:
                await self.hass.services.async_call(
                    "climate", "set_hvac_mode",
                    {"entity_id": self._heater, "hvac_mode": HVACMode.OFF},
                    blocking=False
                )
            if self._cooler:
                await self.hass.services.async_call(
                    "climate", "set_hvac_mode",
                    {"entity_id": self._cooler, "hvac_mode": HVACMode.OFF},
                    blocking=False
                )
            self._last_command_ts = now
            return

        # HEAT
        if self._attr_hvac_mode == HVACMode.HEAT and self._heater:
            await self.hass.services.async_call(
                "climate", "set_temperature",
                {"entity_id": self._heater, "temperature": float(self._attr_target_temperature)},
                blocking=False
            )
            await self.hass.services.async_call(
                "climate", "set_hvac_mode",
                {"entity_id": self._heater, "hvac_mode": HVACMode.HEAT},
                blocking=False
            )
            if self._cooler:
                await self.hass.services.async_call(
                    "climate", "set_hvac_mode",
                    {"entity_id": self._cooler, "hvac_mode": HVACMode.OFF},
                    blocking=False
                )

        # COOL
        if self._attr_hvac_mode == HVACMode.COOL and self._cooler:
            await self.hass.services.async_call(
                "climate", "set_temperature",
                {"entity_id": self._cooler, "temperature": float(self._attr_target_temperature)},
                blocking=False
            )
            await self.hass.services.async_call(
                "climate", "set_hvac_mode",
                {"entity_id": self._cooler, "hvac_mode": HVACMode.COOL},
                blocking=False
            )
            if self._heater:
                await self.hass.services.async_call(
                    "climate", "set_hvac_mode",
                    {"entity_id": self._heater, "hvac_mode": HVACMode.OFF},
                    blocking=False
                )

        self._last_command_ts = now

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self.entry.entry_id}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": self._name,
            "manufacturer": "Eco Thermostat",
            "model": "Virtual Climate",
            "sw_version": "3.0.0",
        }
