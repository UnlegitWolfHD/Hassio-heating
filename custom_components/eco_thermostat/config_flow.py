from __future__ import annotations
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
    CONF_OVERRIDE_THERMOSTAT,
    CONF_OVERRIDE_ENTITY,
    CONF_OVERRIDE_MODE,
    CONF_TEMP_OFFSET,
    CONF_WINDOWS,
    CONF_DEADBAND,
    CONF_MIN_RUN_SECONDS,
    CONF_MIN_IDLE_SECONDS,
    CONF_WINDOW_MODE,
    CONF_FROST_TEMP,
    CONF_SMOOTHING_ALPHA,
    CONF_PRESETS,
    DEFAULT_PRESETS,
    DEFAULT_OPTIONS,
)

OVERRIDE_MODES = {
    "external_value": "Externe Temperatur setzen",
    "offset_mode": "Offset berechnen (Raumtemp - lokale Temp)",
    "disabled": "Deaktiviert"
}


class EcoThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config-Flow für das Eco-Thermostat-Integration-Setup."""

    VERSION = 5

    async def async_step_user(self, user_input=None):
        """Erste Einrichtung über die UI."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
                options=DEFAULT_OPTIONS,
            )

        schema = vol.Schema(
            {
                # Allgemeines
                vol.Required(CONF_NAME, default="Eco Thermostat"): str,

                # Geräte
                vol.Required(CONF_HEATER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Optional(CONF_COOLER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),

                # Sensoren
                vol.Required(CONF_SENSOR_TEMP): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                vol.Optional(CONF_SENSOR_HUM): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
                ),

                # Fensterkontakte
                vol.Optional(CONF_WINDOWS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                        device_class=["opening", "window", "door"],
                        multiple=True
                    )
                ),

                # Override-Einstellungen
                vol.Optional(CONF_OVERRIDE_THERMOSTAT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Optional(CONF_OVERRIDE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["number", "input_number"])
                ),
                vol.Optional(CONF_OVERRIDE_MODE, default="external_value"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(label="Externe Temperatur setzen", value="external_value"),
                            selector.SelectOptionDict(label="Offset berechnen (Raumtemp - lokale Temp)", value="offset_mode"),
                            selector.SelectOptionDict(label="Deaktiviert", value="disabled")
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),

                # Temperatur-Offset
                vol.Optional(CONF_TEMP_OFFSET, default=0.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-10.0,
                        max=10.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C"
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return EcoThermostatOptionsFlow(entry)


class EcoThermostatOptionsFlow(config_entries.OptionsFlow):
    """Options-Flow für Eco Thermostat."""

    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        opts = {**DEFAULT_OPTIONS, **self.entry.options}

        if user_input is not None:
            presets = opts.get(CONF_PRESETS, DEFAULT_PRESETS)
            if CONF_PRESETS in user_input:
                presets = user_input[CONF_PRESETS]
            new_opts = {**opts, **user_input, CONF_PRESETS: presets}
            return self.async_create_entry(title="", data=new_opts)

        schema = vol.Schema({
            vol.Optional(CONF_DEADBAND, default=opts[CONF_DEADBAND]): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=2.0,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="°C"
                )
            ),
            vol.Optional(CONF_MIN_RUN_SECONDS, default=opts[CONF_MIN_RUN_SECONDS]): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=3600,
                    step=10,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s"
                )
            ),
            vol.Optional(CONF_MIN_IDLE_SECONDS, default=opts[CONF_MIN_IDLE_SECONDS]): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=3600,
                    step=10,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s"
                )
            ),
            vol.Optional(CONF_WINDOW_MODE, default=opts[CONF_WINDOW_MODE]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(label="Ausschalten", value="off"),
                        selector.SelectOptionDict(label="Frostschutz", value="frost")
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Optional(CONF_FROST_TEMP, default=opts[CONF_FROST_TEMP]): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=3.0,
                    max=12.0,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="°C"
                )
            ),
            vol.Optional(CONF_SMOOTHING_ALPHA, default=opts[CONF_SMOOTHING_ALPHA]): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.0,
                    max=1.0,
                    step=0.05,
                    mode=selector.NumberSelectorMode.SLIDER
                )
            ),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
