from __future__ import annotations

DOMAIN = "eco_thermostat"

# Konfigurationsschlüssel
CONF_NAME = "name"
CONF_HEATER = "heater"
CONF_COOLER = "cooler"
CONF_SENSOR_TEMP = "sensor_temp"
CONF_SENSOR_HUM = "sensor_humidity"
CONF_OVERRIDE_THERMOSTAT = "override_thermostat"
CONF_OVERRIDE_ENTITY = "override_entity"
CONF_OVERRIDE_MODE = "override_mode"
CONF_TEMP_OFFSET = "temp_offset"
CONF_WINDOWS = "windows"

# Optionen
CONF_DEADBAND = "deadband"
CONF_MIN_RUN_SECONDS = "min_run_seconds"
CONF_MIN_IDLE_SECONDS = "min_idle_seconds"
CONF_WINDOW_MODE = "window_mode"
CONF_FROST_TEMP = "frost_temp"
CONF_SMOOTHING_ALPHA = "smoothing_alpha"
CONF_PRESETS = "presets"

DEFAULT_PRESETS = {
    "eco": 18.0,
    "comfort": 22.0,
    "sleep": 19.0,
    "away": 16.0
}

DEFAULT_OPTIONS = {
    CONF_DEADBAND: 0.4,
    CONF_MIN_RUN_SECONDS: 180,
    CONF_MIN_IDLE_SECONDS: 180,
    CONF_WINDOW_MODE: "frost",
    CONF_FROST_TEMP: 5.0,
    CONF_SMOOTHING_ALPHA: 0.0,
    CONF_PRESETS: DEFAULT_PRESETS
}
