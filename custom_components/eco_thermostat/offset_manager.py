"""Offset manager for automatic local temperature offset adjustment."""
import logging
from typing import Optional

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class OffsetManager:
    """Manage automatic offset adjustments for thermostats."""

    def __init__(
        self,
        hass: HomeAssistant,
        heater_entity: str,
        heater_offset_entity: Optional[str],
        cooler_entity: Optional[str],
        cooler_offset_entity: Optional[str],
        auto_update_enabled: bool,
    ):
        """Initialize offset manager."""
        self.hass = hass
        self.heater_entity = heater_entity
        self.heater_offset_entity = heater_offset_entity
        self.cooler_entity = cooler_entity
        self.cooler_offset_entity = cooler_offset_entity
        self.auto_update_enabled = auto_update_enabled

    async def update_offsets(self, sensor_temp: Optional[float]) -> None:
        """Update thermostat local temperature offsets based on sensor difference."""
        if not self.auto_update_enabled or sensor_temp is None:
            return

        # Update heater offset
        if self.heater_entity and self.heater_offset_entity:
            await self._update_device_offset(
                self.heater_entity,
                self.heater_offset_entity,
                sensor_temp,
                "Heater"
            )

        # Update cooler offset
        if self.cooler_entity and self.cooler_offset_entity:
            await self._update_device_offset(
                self.cooler_entity,
                self.cooler_offset_entity,
                sensor_temp,
                "Cooler"
            )

    async def _update_device_offset(
        self,
        device_entity: str,
        offset_entity: str,
        sensor_temp: float,
        device_name: str,
    ) -> None:
        """Update offset for a specific device."""
        # Get current local temperature from the thermostat
        thermostat_state = self.hass.states.get(device_entity)
        if not thermostat_state:
            _LOGGER.debug("%s entity %s not found", device_name, device_entity)
            return

        local_temp = thermostat_state.attributes.get("current_temperature")
        if local_temp is None:
            _LOGGER.debug("%s %s has no local temperature", device_name, device_entity)
            return

        try:
            local_temp = float(local_temp)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid local temperature from %s: %s", device_entity, local_temp)
            return

        # Get current offset value
        offset_state = self.hass.states.get(offset_entity)
        if not offset_state:
            _LOGGER.debug("Offset entity %s not found", offset_entity)
            return

        try:
            current_offset = float(offset_state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid offset value from %s: %s", offset_entity, offset_state.state)
            current_offset = 0.0

        # Calculate new offset
        # Formula: new_offset = current_offset + (sensor_temp - local_temp)
        # This adjusts the thermostat's local sensor to match our reference sensor
        temperature_difference = sensor_temp - local_temp
        new_offset = round(current_offset + temperature_difference, 1)

        # Only update if difference is significant (> 0.1°C)
        if abs(new_offset - current_offset) < 0.1:
            _LOGGER.debug(
                "%s offset unchanged: %.1f°C (diff: %.1f°C)",
                device_name,
                current_offset,
                temperature_difference
            )
            return

        # Apply the new offset
        try:
            domain = offset_entity.split(".")[0]
            await self.hass.services.async_call(
                domain,
                "set_value",
                {"entity_id": offset_entity, "value": new_offset},
                blocking=False,
            )
            _LOGGER.info(
                "%s offset updated: %.1f°C -> %.1f°C (sensor: %.1f°C, local: %.1f°C, diff: %.1f°C)",
                device_name,
                current_offset,
                new_offset,
                sensor_temp,
                local_temp,
                temperature_difference
            )
        except Exception as err:
            _LOGGER.error("Failed to update %s offset: %s", device_name, err)
