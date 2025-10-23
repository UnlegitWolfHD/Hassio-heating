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
    CONF_TEMP_OFFSET,
    CONF_WINDOWS,
    DEFAULT_OPTIONS,
    CONF_DEADBAND,
    CONF_MIN_RUN_SECONDS,
    CONF_MIN_IDLE_SECONDS,
    CONF_WINDOW_MODE,
    CONF_FROST_TEMP,
    CONF_SMOOTHING_ALPHA,
    CONF_PRESETS,
    DEFAULT_PRESETS,
)


class EcoThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config-Flow für das Eco-Thermostat-Integration-Setup."""

    VERSION = 4

    async def async_step_user(self, user_input=None):
        """Haupt-Einrichtungsschritt über die UI."""
        if user_input is not None:
            # Direktes Erstellen des Eintrags mit Default-Optionen
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
                options=DEFAULT_OPTIONS,
            )

        schema = vol.Schema(
            {
                # Grundinformationen
                vol.Required(CONF_NAME, default="Eco Thermostat"): str,

                # Geräte
                vol.Required(CONF_HEATER): selector.selector(
                    {"entity": {"domain": "climate"}}
                ),
                vol.Optional(CONF_COOLER): selector.selector(
                    {"entity": {"domain": "climate"}}
                ),

                # Sensoren
                vol.Required(CONF_SENSOR_TEMP): selector.selector(
                    {
                        "entity": {
                            "domain": "sensor",
                            "device_class": "temperature",
                        }
                    }
                ),
                vol.Optional(CONF_SENSOR_HUM): selector.selector(
                    {
                        "entity": {
                            "domain": "sensor",
                            "device_class": "humidity",
                        }
                    }
                ),

                # Override-Optionen
                vol.Optional(CONF_OVERRIDE_THERMOSTAT): selector.selector(
                    {"entity": {"domain": "climate"}}
                ),
                vol.Optional(CONF_OVERRIDE_ENTITY): selector.selector(
                    {
                        "entity": {
                            "domain": ["number", "input_number", "select"],
                        }
                    }
                ),

                # Temperatur-Offset
                vol.Optional(CONF_TEMP_OFFSET, default=0.0): vol.Coerce(float),

                # Fensterkontakte (Mehrfachauswahl)
                vol.Optional(CONF_WINDOWS): selector.selector(
                    {
                        "entity": {
                            "domain": "binary_sensor",
                            # erlaubt window, door oder opening
                            "device_class": ["opening", "window", "door"],
                        },
                        "multiple": True,
                    }
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    # ----------------------------------------------------------------------

    @staticmethod
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        """Ermöglicht Öffnen des Optionsdialogs."""
        return EcoThermostatOptionsFlow(entry)


class EcoThermostatOptionsFlow(config_entries.OptionsFlow):
    """Options-Flow für das Eco-Thermostat."""

    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Erster Optionsschritt – Steuerparameter."""
        opts = {**DEFAULT_OPTIONS, **self.entry.options}

        if user_input is not None:
            presets = opts.get(CONF_PRESETS, DEFAULT_PRESETS)
            if CONF_PRESETS in user_input:
                presets = user_input[CONF_PRESETS]

            new_opts = {**opts, **user_input, CONF_PRESETS: presets}
            return self.async_create_entry(title="", data=new_opts)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DEADBAND, default=opts[CONF_DEADBAND]
                ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=2.0)),

                vol.Optional(
                    CONF_MIN_RUN_SECONDS, default=opts[CONF_MIN_RUN_SECONDS]
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),

                vol.Optional(
                    CONF_MIN_IDLE_SECONDS, default=opts[CONF_MIN_IDLE_SECONDS]
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),

                vol.Optional(
                    CONF_WINDOW_MODE, default=opts[CONF_WINDOW_MODE]
                ): vol.In(["off", "frost"]),

                vol.Optional(
                    CONF_FROST_TEMP, default=opts[CONF_FROST_TEMP]
                ): vol.All(vol.Coerce(float), vol.Range(min=3, max=12)),

                vol.Optional(
                    CONF_SMOOTHING_ALPHA, default=opts[CONF_SMOOTHING_ALPHA]
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
