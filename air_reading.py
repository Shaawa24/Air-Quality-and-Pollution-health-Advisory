import re
from datetime import datetime


class AirReading:
    def __init__(self, location_name, latitude, longitude, timestamp=None):
        self.location_name = location_name
        self.latitude = latitude
        self.longitude = longitude
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.aqi = None
        self.pm25 = None
        self.pm10 = None
        self.ozone = None
        self.no2 = None
        self.source = "open-meteo"

    def extract_number(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        match = re.search(r"-?\d+\.?\d*", text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    def set_from_api_data(self, current_data):
        if not current_data or not isinstance(current_data, dict):
            return False
        self.aqi = self.extract_number(current_data.get("us_aqi") or current_data.get("european_aqi"))
        self.pm25 = self.extract_number(current_data.get("pm2_5"))
        self.pm10 = self.extract_number(current_data.get("pm10"))
        self.ozone = self.extract_number(current_data.get("ozone"))
        self.no2 = self.extract_number(current_data.get("nitrogen_dioxide"))
        return True

    def to_dict(self):
        return {
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp,
            "aqi": self.aqi,
            "pm25": self.pm25,
            "pm10": self.pm10,
            "ozone": self.ozone,
            "no2": self.no2,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data):
        reading = cls(
            data.get("location_name", "Unknown"),
            data.get("latitude"),
            data.get("longitude"),
            data.get("timestamp")
        )
        reading.aqi = data.get("aqi")
        reading.pm25 = data.get("pm25")
        reading.pm10 = data.get("pm10")
        reading.ozone = data.get("ozone")
        reading.no2 = data.get("no2")
        reading.source = data.get("source", "open-meteo")
        return reading

    def has_missing_data(self):
        return self.aqi is None and self.pm25 is None and self.pm10 is None

    def summary(self):
        parts = [f"Location: {self.location_name}", f"Time: {self.timestamp}"]
        if self.aqi is not None:
            parts.append(f"AQI: {self.aqi}")
        if self.pm25 is not None:
            parts.append(f"PM2.5: {self.pm25} ug/m3")
        if self.pm10 is not None:
            parts.append(f"PM10: {self.pm10} ug/m3")
        if self.ozone is not None:
            parts.append(f"Ozone: {self.ozone} ug/m3")
        if self.no2 is not None:
            parts.append(f"NO2: {self.no2} ug/m3")
        return " | ".join(parts)


if __name__ == "__main__":
    print("Testing AirReading class...")
    sample_current = {
        "us_aqi": 42,
        "pm2_5": 12.5,
        "pm10": 18.3,
        "ozone": 65.0,
        "nitrogen_dioxide": 15.2
    }
    reading = AirReading("Abuja, Nigeria", 9.08, 7.40)
    success = reading.set_from_api_data(sample_current)
    print("Set from data:", success)
    print(reading.summary())
    print("Has missing data:", reading.has_missing_data())
    d = reading.to_dict()
    print("Dict keys:", list(d.keys()))
    restored = AirReading.from_dict(d)
    print("Restored summary:", restored.summary())
    print("Extract from '12.5 ug':", reading.extract_number("12.5 ug"))
    print("Extract from None:", reading.extract_number(None))
