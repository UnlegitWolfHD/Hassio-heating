class SensorManager:
    def __init__(self, hass, data):
        self.hass = hass
        self.data = data
        self.current_temp = None
        self.current_hum = None

    async def refresh(self):
        # TODO: Temperatur & Humidity vom externen Sensor holen
        pass
