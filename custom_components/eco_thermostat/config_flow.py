"""Config flow for Eco Thermostat."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_HEATER,
    CONF_COOLER,
    CONF_SENSOR_TEMP,
    CONF_SENSOR_HUM,
    CONF_TEMP_OFFSET,
    CONF_WINDOWS,
    CONF_DEADBAND,
    CONF_MIN_RUN,
    CONF_MIN_IDLE,
    CONF_WINDOW_MODE,
    CONF_FROST_TEMP,
    CONF_SMOOTHING_ALPHA,
    CONF_PRESET_ECO,
    CONF_PRESET_COMFORT,
    CONF_PRESET_SLEEP,
    CONF_PRESET_AWAY,
    DEFAULT_NAME,
    DEFAULT_DEADBAND,
    DEFAULT_MIN_RUN,
    DEFAULT_MIN_IDLE,
    DEFAULT_WINDOW_MODE,
    DEFAULT_FROST_TEMP,
    DEFAULT_SMOOTHING_ALPHA,
    DEFAULT_TEMP_OFFSET,
    DEFAULT_PRESET_ECO,
    DEFAULT_PRESET_COMFORT,
    DEFAULT_PRESET_SLEEP,
    DEFAULT_PRESET_AWAY,
)


class EcoThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eco Thermostat."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Create entry with default options
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
                options={
                    CONF_DEADBAND: DEFAULT_DEADBAND,
                    CONF_MIN_RUN: DEFAULT_MIN_RUN,
                    CONF_MIN_IDLE: DEFAULT_MIN_IDLE,
                    CONF_WINDOW_MODE: DEFAULT_WINDOW_MODE,
                    CONF_FROST_TEMP: DEFAULT_FROST_TEMP,
                    CONF_SMOOTHING_ALPHA: DEFAULT_SMOOTHING_ALPHA,
                    CONF_PRESET_ECO: DEFAULT_PRESET_ECO,
                    CONF_PRESET_COMFORT: DEFAULT_PRESET_COMFORT,
                    CONF_PRESET_SLEEP: DEFAULT_PRESET_SLEEP,
                    CONF_PRESET_AWAY: DEFAULT_PRESET_AWAY,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HEATER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Optional(CONF_COOLER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Required(CONF_SENSOR_TEMP): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="temperature"
                    )
                ),
                vol.Optional(CONF_SENSOR_HUM): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="humidity"
                    )
                ),
                vol.Optional(CONF_TEMP_OFFSET, default=DEFAULT_TEMP_OFFSET): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-10.0,
                        max=10.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C"
                    )
                ),
                vol.Optional(CONF_WINDOWS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                        multiple=True
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    def async_get_options_flow(entry):
        """Get the options flow."""
        return EcoThermostatOptionsFlow(entry)


class EcoThermostatOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.entry.options

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DEADBAND,
                    default=options.get(CONF_DEADBAND, DEFAULT_DEADBAND)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=2.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C"
                    )
                ),
                vol.Optional(
                    CONF_MIN_RUN,
                    default=options.get(CONF_MIN_RUN, DEFAULT_MIN_RUN)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=3600,
                        step=10,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_MIN_IDLE,
                    default=options.get(CONF_MIN_IDLE, DEFAULT_MIN_IDLE)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=3600,
                        step=10,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_WINDOW_MODE,
                    default=options.get(CONF_WINDOW_MODE, DEFAULT_WINDOW_MODE)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["off", "frost"],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Optional(
                    CONF_FROST_TEMP,
                    default=options.get(CONF_FROST_TEMP, DEFAULT_FROST_TEMP)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=3.0,
                        max=12.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C"
                    )
                ),
                vol.Optional(
                    CONF_SMOOTHING_ALPHA,
                    default=options.get(CONF_SMOOTHING_ALPHA, DEFAULT_SMOOTHING_ALPHA)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_PRESET_ECO,
                    default=options.get(CONF_PRESET_ECO, DEFAULT_PRESET_ECO)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10.0,
                        max=30.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C"
                    )
                ),
                vol.Optional(
                    CONF_PRESET_COMFORT,
                    default=options.get(CONF_PRESET_COMFORT, DEFAULT_PRESET_COMFORT)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10.0,
                        max=30.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C"
                    )
                ),
                vol.Optional(
                    CONF_PRESET_SLEEP,
                    default=options.get(CONF_PRESET_SLEEP, DEFAULT_PRESET_SLEEP)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10.0,
                        max=30.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C"
                    )
                ),
                vol.Optional(
                    CONF_PRESET_AWAY,
                    default=options.get(CONF_PRESET_AWAY, DEFAULT_PRESET_AWAY)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10.0,
                        max=30.0,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C"
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
