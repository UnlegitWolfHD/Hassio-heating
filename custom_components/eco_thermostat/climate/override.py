import logging
from homeassistant.components.climate.const import HVACMode

_LOGGER = logging.getLogger(__name__)


class OverrideHandler:
    def __init__(self, hass, data):
        self.hass = hass
        self.data = data
        self.override_thermostat = data.get("override_thermostat")

    async def apply(self, control, sensors):
        """Synchronisiere externen Sensor & Sollwert ins Override-Thermostat"""
        if not self.override_thermostat:
            return

        try:
            # 1) Externe Temperatur als Istwert setzen
            if sensors.current_temp is not None:
                # Nicht alle Thermostate erlauben override von current_temperature.
                # Fallback: Wir setzen einfach erneut das Target, damit HA synchron bleibt.
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {
                        "entity_id": self.override_thermostat,
                        "temperature": control.target_temp
                    },
                    blocking=False
                )

            # 2) HVAC Mode synchronisieren
            if control.hvac_mode in (HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF):
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {
                        "entity_id": self.override_thermostat,
                        "hvac_mode": control.hvac_mode
                    },
                    blocking=False
                )

        except Exception as e:
            _LOGGER.warning("OverrideHandler Fehler bei %s: %s", self.override_thermostat, e)
