from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    from .climate import EcoThermostatEntity
    hass.async_create_task(hass.helpers.entity_platform.async_add_entities([EcoThermostatEntity(hass, entry)]))
    return True
