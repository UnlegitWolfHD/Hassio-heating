from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import (
    DOMAIN, CONF_NAME, CONF_HEATER, CONF_COOLER, CONF_SENSOR, CONF_TEMP_OFFSET,
    CONF_WINDOWS, DEFAULT_OPTIONS, CONF_DEADBAND, CONF_MIN_RUN_SECONDS,
    CONF_MIN_IDLE_SECONDS, CONF_WINDOW_MODE, CONF_FROST_TEMP,
    CONF_SMOOTHING_ALPHA, CONF_PRESETS, DEFAULT_PRESETS
)

class EcoThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # store defaults for options
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
                options=DEFAULT_OPTIONS
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Eco Thermostat"): str,
                vol.Required(CONF_HEATER): selector.selector({"entity": {"domain": "climate"}}),
                vol.Optional(CONF_COOLER): selector.selector({"entity": {"domain": "climate"}}),
                vol.Required(CONF_SENSOR): selector.selector({"entity": {
                    "domain": "sensor", "device_class": "temperature"
                }}),
                vol.Optional(CONF_TEMP_OFFSET, default=0.0): vol.Coerce(float),
                vol.Optional(CONF_WINDOWS, default=[]): selector.selector({
                    "entity": {"domain": "binary_sensor", "device_class": "opening", "multiple": True}
                }),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return EcoThermostatOptionsFlow(entry)


class EcoThermostatOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        opts = {**DEFAULT_OPTIONS, **self.entry.options}

        if user_input is not None:
            # preserve presets in a separate step or keep if provided
            presets = opts.get(CONF_PRESETS, DEFAULT_PRESETS)
            if CONF_PRESETS in user_input:
                presets = user_input[CONF_PRESETS]
            new_opts = {**opts, **user_input, CONF_PRESETS: presets}
            return self.async_create_entry(title="", data=new_opts)

        schema = vol.Schema(
            {
                vol.Optional(CONF_DEADBAND, default=opts[CONF_DEADBAND]): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=2.0)),
                vol.Optional(CONF_MIN_RUN_SECONDS, default=opts[CONF_MIN_RUN_SECONDS]): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
                vol.Optional(CONF_MIN_IDLE_SECONDS, default=opts[CONF_MIN_IDLE_SECONDS]): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
                vol.Optional(CONF_WINDOW_MODE, default=opts[CONF_WINDOW_MODE]): vol.In(["off", "frost"]),
                vol.Optional(CONF_FROST_TEMP, default=opts[CONF_FROST_TEMP]): vol.All(vol.Coerce(float), vol.Range(min=3, max=12)),
                vol.Optional(CONF_SMOOTHING_ALPHA, default=opts[CONF_SMOOTHING_ALPHA]): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_presets(self, user_input=None):
        # Optional: separater Schritt, falls du Presets anders pflegen willst.
        opts = {**DEFAULT_OPTIONS, **self.entry.options}
        presets = opts.get(CONF_PRESETS, DEFAULT_PRESETS)

        if user_input is not None:
            new_presets = {
                "eco": float(user_input["eco"]),
                "comfort": float(user_input["comfort"]),
                "sleep": float(user_input["sleep"]),
                "away": float(user_input["away"]),
            }
            new_opts = {**opts, CONF_PRESETS: new_presets}
            return self.async_create_entry(title="", data=new_opts)

        schema = vol.Schema(
            {
                vol.Required("eco", default=presets["eco"]): vol.Coerce(float),
                vol.Required("comfort", default=presets["comfort"]): vol.Coerce(float),
                vol.Required("sleep", default=presets["sleep"]): vol.Coerce(float),
                vol.Required("away", default=presets["away"]): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="presets", data_schema=schema)
