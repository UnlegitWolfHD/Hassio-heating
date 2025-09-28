from homeassistant.components.climate.const import HVACMode

class ControlLogic:
    def __init__(self, hass, entry, heater, cooler):
        self.hass = hass
        self.entry = entry
        self.heater = heater
        self.cooler = cooler
        self.presets = {"eco": 18, "comfort": 22, "sleep": 19, "away": 16}
        self.hvac_mode = HVACMode.HEAT
        self.target_temp = 22.0
        self.preset_mode = "comfort"

    def supported_modes(self, cooler):
        return [HVACMode.OFF, HVACMode.HEAT] + ([HVACMode.COOL, HVACMode.AUTO] if cooler else [])

    async def set_target(self, t: float):
        self.target_temp = t

    async def set_mode(self, mode: HVACMode):
        self.hvac_mode = mode

    async def set_preset(self, preset: str):
        if preset in self.presets:
            self.preset_mode = preset
            self.target_temp = self.presets[preset]

    async def evaluate(self, sensors):
        # TODO: Deadband, Fenster, Auto-Mode Logik implementieren
        pass
