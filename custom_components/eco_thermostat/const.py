"""Konstanten für Eco Thermostat."""

DOMAIN = "eco_thermostat"

# Config Keys
CONF_NAME = "name"
CONF_HEATER = "heater"
CONF_COOLER = "cooler"
CONF_SENSOR_TEMP = "sensor_temp"
CONF_SENSOR_HUM = "sensor_humidity"
CONF_TEMP_OFFSET = "temp_offset"
CONF_WINDOWS = "windows"
CONF_HEATER_OFFSET_ENTITY = "heater_offset_entity"
CONF_COOLER_OFFSET_ENTITY = "cooler_offset_entity"
CONF_AUTO_OFFSET_ENABLED = "auto_offset_enabled"

# Options
CONF_DEADBAND = "deadband"
CONF_MIN_RUN = "min_run_seconds"
CONF_MIN_IDLE = "min_idle_seconds"
CONF_WINDOW_MODE = "window_mode"
CONF_FROST_TEMP = "frost_temp"
CONF_SMOOTHING_ALPHA = "smoothing_alpha"
CONF_AUTO_OFFSET_UPDATE = "auto_offset_update"

# Presets
CONF_PRESET_ECO = "preset_eco"
CONF_PRESET_COMFORT = "preset_comfort"
CONF_PRESET_SLEEP = "preset_sleep"
CONF_PRESET_AWAY = "preset_away"

# Defaults
DEFAULT_NAME = "Eco Thermostat"
DEFAULT_DEADBAND = 0.5
DEFAULT_MIN_RUN = 180
DEFAULT_MIN_IDLE = 180
DEFAULT_WINDOW_MODE = "frost"
DEFAULT_FROST_TEMP = 5.0
DEFAULT_SMOOTHING_ALPHA = 0.0
DEFAULT_TEMP_OFFSET = 0.0

DEFAULT_PRESET_ECO = 18.0
DEFAULT_PRESET_COMFORT = 22.0
DEFAULT_PRESET_SLEEP = 19.0
DEFAULT_PRESET_AWAY = 16.0
DEFAULT_AUTO_OFFSET_UPDATE = True
DEFAULT_AUTO_OFFSET_UPDATE = True
