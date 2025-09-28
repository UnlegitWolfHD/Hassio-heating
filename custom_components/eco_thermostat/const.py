from __future__ import annotations

DOMAIN = "eco_thermostat"

# Config keys
CONF_NAME = "name"
CONF_HEATER = "heater"
CONF_COOLER = "cooler"
CONF_SENSOR = "sensor"
CONF_TEMP_OFFSET = "temp_offset"
CONF_WINDOWS = "windows"

# Options (modifiable via OptionsFlow)
CONF_DEADBAND = "deadband"
CONF_MIN_RUN_SECONDS = "min_run_seconds"
CONF_MIN_IDLE_SECONDS = "min_idle_seconds"
CONF_WINDOW_MODE = "window_mode"          # "off" | "frost"
CONF_FROST_TEMP = "frost_temp"
CONF_SMOOTHING_ALPHA = "smoothing_alpha"  # 0..1 EMA, 0 = aus
CONF_PRESETS = "presets"

DEFAULT_PRESETS = {
    "eco": 18.0,
    "comfort": 22.0,
    "sleep": 19.0,
    "away": 16.0,
}

DEFAULT_OPTIONS = {
    CONF_DEADBAND: 0.4,           # °C Hysterese
    CONF_MIN_RUN_SECONDS: 180,    # min. Laufzeit bevor umgeschaltet wird
    CONF_MIN_IDLE_SECONDS: 180,   # min. Stillstand bevor wieder gestartet wird
    CONF_WINDOW_MODE: "frost",
    CONF_FROST_TEMP: 5.0,
    CONF_SMOOTHING_ALPHA: 0.0,    # 0 = keine Glättung
    CONF_PRESETS: DEFAULT_PRESETS,
}
