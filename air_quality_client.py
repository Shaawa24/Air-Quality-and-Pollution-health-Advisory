import re
import requests
from datetime import datetime


class AirQualityClient:
    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
    GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self):
        self.last_error = None

    def validate_coordinates(self, lat, lon):
        lat_str = str(lat).strip()
        lon_str = str(lon).strip()
        coord_pattern = r"^-?\d+(\.\d+)?$"
        if not re.match(coord_pattern, lat_str) or not re.match(coord_pattern, lon_str):
            return False
        try:
            lat_f = float(lat_str)
            lon_f = float(lon_str)
            if lat_f < -90 or lat_f > 90:
                return False
            if lon_f < -180 or lon_f > 180:
                return False
            return True
        except ValueError:
            return False

    def validate_location_input(self, location):
        if not location or not isinstance(location, str):
            return False
        location = location.strip()
        if len(location) < 2:
            return False
        pattern = r"^[a-zA-Z0-9\s,\.\-]+$"
        if not re.match(pattern, location):
            return False
        return True

    def get_coordinates(self, location):
        location = location.strip()
        coord_match = re.match(r"^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$", location)
        if coord_match:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if self.validate_coordinates(lat, lon):
                return lat, lon, location
            else:
                self.last_error = "Invalid coordinates"
                return None, None, None

        if not self.validate_location_input(location):
            self.last_error = "Invalid location input"
            return None, None, None

        try:
            params = {"name": location, "count": 1, "language": "en", "format": "json"}
            response = requests.get(self.GEO_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "results" not in data or len(data["results"]) == 0:
                self.last_error = "Location not found"
                return None, None, None
            result = data["results"][0]
            lat = result["latitude"]
            lon = result["longitude"]
            name = result.get("name", location)
            country = result.get("country", "")
            display = f"{name}, {country}" if country else name
            return lat, lon, display
        except requests.exceptions.Timeout:
            self.last_error = "Network timeout while searching location"
            return None, None, None
        except requests.exceptions.RequestException as e:
            self.last_error = f"Network error: {str(e)}"
            return None, None, None
        except (KeyError, ValueError, TypeError):
            self.last_error = "Failed to parse location data"
            return None, None, None

    def fetch_air_quality(self, latitude, longitude, forecast_days=3):
        if not self.validate_coordinates(latitude, longitude):
            self.last_error = "Invalid coordinates"
            return None

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "pm10,pm2_5,ozone,nitrogen_dioxide,european_aqi,us_aqi",
            "hourly": "pm10,pm2_5,ozone,nitrogen_dioxide,european_aqi,us_aqi",
            "forecast_days": forecast_days,
            "timezone": "auto"
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                self.last_error = data.get("reason", "API error")
                return None
            return data
        except requests.exceptions.Timeout:
            self.last_error = "Request timed out"
            return None
        except requests.exceptions.ConnectionError:
            self.last_error = "Network connection error"
            return None
        except requests.exceptions.HTTPError as e:
            self.last_error = f"HTTP error: {e}"
            return None
        except requests.exceptions.RequestException as e:
            self.last_error = f"Request failed: {str(e)}"
            return None
        except ValueError:
            self.last_error = "Invalid JSON response"
            return None


if __name__ == "__main__":
    client = AirQualityClient()
    print("Testing AirQualityClient...")
    print("Validating coordinates 9.08, 7.40:", client.validate_coordinates(9.08, 7.40))
    print("Validating location 'Abuja':", client.validate_location_input("Abuja"))
    lat, lon, name = client.get_coordinates("Abuja")
    if lat is not None:
        print(f"Found: {name} ({lat}, {lon})")
        data = client.fetch_air_quality(lat, lon)
        if data:
            print("Current AQI (US):", data.get("current", {}).get("us_aqi"))
            print("Current PM2.5:", data.get("current", {}).get("pm2_5"))
            print("Fetch successful.")
        else:
            print("Fetch failed:", client.last_error)
    else:
        print("Location lookup failed:", client.last_error)
