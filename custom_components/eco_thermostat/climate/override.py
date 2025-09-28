class OverrideHandler:
    def __init__(self, hass, data):
        self.hass = hass
        self.data = data
        self.override_thermostat = data.get("override_thermostat")

    async def apply(self, control, sensors):
        if not self.override_thermostat:
            return
        # TODO: override Logik auf echtes Thermostat anwenden
        pass
