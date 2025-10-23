import logging
from typing import Optional
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class OverrideHandler:
    """Behandelt optionale Overrides von Zielwerten an echte Climate- oder Number-Entities."""

    def __init__(self, hass: HomeAssistant, data: dict) -> None:
        self.hass = hass
        self.override_climate: Optional[str] = data.get("override_thermostat")
        self.override_entity: Optional[str] = data.get("override_entity")

    # -------------------------------------------------------------------------

    async def apply(self, control, sensors) -> None:
        """
        Überträgt Solltemperatur und Modus in echte Thermostate oder Sub-Entities.
        Wird nach jeder Regelbewertung aufgerufen.
        """
        await self._apply_climate_override(control)
        await self._apply_entity_override(sensors)

    # -------------------------------------------------------------------------

    async def _apply_climate_override(self, control) -> None:
        """Überschreibt Zieltemperatur und Modus in einem realen Climate-Entity."""
        if not self.override_climate:
            return

        state = self.hass.states.get(self.override_climate)
        if not state:
            _LOGGER.debug("Override-Climate %s existiert nicht.", self.override_climate)
            return

        try:
            # Zieltemperatur setzen
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": self.override_climate,
                    "temperature": float(control.target_temp),
                },
                blocking=True,
            )

            # Modus setzen
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {
                    "entity_id": self.override_climate,
                    "hvac_mode": control.hvac_mode,
                },
                blocking=True,
            )

            _LOGGER.debug(
                "Override Climate gesetzt: %s → %.1f°C (%s)",
                self.override_climate,
                control.target_temp,
                control.hvac_mode,
            )

        except Exception as e:
            _LOGGER.warning(
                "Fehler beim Überschreiben des Climate %s: %s",
                self.override_climate,
                e,
            )

    # -------------------------------------------------------------------------

    async def _apply_entity_override(self, sensors) -> None:
        """Überschreibt z. B. number.* oder input_number.* mit aktuellem Temperaturwert."""
        if not self.override_entity or sensors.current_temp is None:
            return

        domain = self.override_entity.split(".")[0]
        service = "set_value" if domain in ("number", "input_number") else None
        if not service:
            _LOGGER.debug("Keine passende Serviceaktion für Override %s", self.override_entity)
            return

        try:
            await self.hass.services.async_call(
                domain,
                service,
                {
                    "entity_id": self.override_entity,
                    "value": float(sensors.current_temp),
                },
                blocking=False,
            )
            _LOGGER.debug(
                "Override Entity gesetzt: %s = %.1f°C",
                self.override_entity,
                sensors.current_temp,
            )

        except Exception as e:
            _LOGGER.warning(
                "Fehler beim Überschreiben der Override-Entity %s: %s",
                self.override_entity,
                e,
            )
