import logging
from typing import Optional
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class OverrideHandler:
    """Setzt externe Werte oder berechnet Offsets je nach Modus."""

    def __init__(self, hass: HomeAssistant, data: dict):
        self.hass = hass
        self.override_climate = data.get("override_thermostat")
        self.override_entity = data.get("override_entity")
        self.override_mode = data.get("override_mode", "external_value")

    async def apply(self, control, sensors):
        if self.override_mode == "disabled":
            return
        await self._apply_override(control, sensors)

    async def _apply_override(self, control, sensors):
        if not self.override_entity or sensors.current_temp is None:
            return
        domain = self.override_entity.split(".")[0]
        if domain not in ("number", "input_number"):
            return
        value = sensors.current_temp
        if self.override_mode == "offset_mode" and self.override_climate:
            state = self.hass.states.get(self.override_climate)
            if state and (lt := state.attributes.get("current_temperature")) is not None:
                value = round(sensors.current_temp - float(lt), 1)
                _LOGGER.debug("Berechneter Offset: %.1f°C", value)
        try:
            await self.hass.services.async_call(domain, "set_value", {
                "entity_id": self.override_entity,
                "value": value
            }, blocking=False)
            _LOGGER.debug("Override %s gesetzt: %.1f°C", self.override_entity, value)
        except Exception as e:
            _LOGGER.warning("Fehler Override %s: %s", self.override_entity, e)
