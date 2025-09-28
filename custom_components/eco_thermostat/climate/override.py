import logging

_LOGGER = logging.getLogger(__name__)


class OverrideHandler:
    def __init__(self, hass, data):
        self.hass = hass
        self.override_climate = data.get("override_thermostat")
        self.override_entity = data.get("override_entity")

    async def apply(self, control, sensors):
        """Überschreibt Werte ins echte Thermostat bzw. dessen Sub-Entity"""
        # 1) Climate Override (hvac_mode / target_temp)
        if self.override_climate:
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {
                        "entity_id": self.override_climate,
                        "temperature": control.target_temp,
                    },
                    blocking=False,
                )
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {
                        "entity_id": self.override_climate,
                        "hvac_mode": control.hvac_mode,
                    },
                    blocking=False,
                )
            except Exception as e:
                _LOGGER.warning("Fehler beim Überschreiben des Climate %s: %s", self.override_climate, e)

        # 2) Direkte Attribut-Entity überschreiben (z. B. number.*)
        if self.override_entity and sensors.current_temp is not None:
            try:
                await self.hass.services.async_call(
                    "number",
                    "set_value",
                    {
                        "entity_id": self.override_entity,
                        "value": float(sensors.current_temp),
                    },
                    blocking=False,
                )
                _LOGGER.debug("Override: %s = %.1f°C", self.override_entity, sensors.current_temp)
            except Exception as e:
                _LOGGER.warning("Fehler beim Überschreiben der Override-Entity %s: %s", self.override_entity, e)
