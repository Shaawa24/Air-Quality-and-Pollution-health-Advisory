import re
import requests


def validate_location_string(text):
    if not text or not isinstance(text, str):
        return False
    text = text.strip()
    if len(text) < 2:
        return False
    pattern = r"^[a-zA-Z0-9\s,\.\-]+$"
    return bool(re.match(pattern, text))


def get_coords(location):
    if not validate_location_string(location):
        return None, None, "Invalid location format"
    coord_match = re.match(r"^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$", location.strip())
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, location
            return None, None, "Coordinates out of range"
        except ValueError:
            return None, None, "Bad coordinates"

    url = "https://geocoding-api.open-meteo.com/v1/search"
    try:
        r = requests.get(url, params={"name": location, "count": 1, "language": "en"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "results" not in data or not data["results"]:
            return None, None, "Location not found"
        res = data["results"][0]
        name = res.get("name", location)
        country = res.get("country", "")
        display = f"{name}, {country}" if country else name
        return res["latitude"], res["longitude"], display
    except requests.exceptions.RequestException as e:
        return None, None, f"Network error: {e}"
    except (KeyError, TypeError, ValueError):
        return None, None, "Parse error"


def fetch_current_aq(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm10,pm2_5,ozone,nitrogen_dioxide,us_aqi,european_aqi",
        "timezone": "auto"
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
        current = data.get("current", {})
        return {
            "aqi": current.get("us_aqi") or current.get("european_aqi"),
            "pm25": current.get("pm2_5"),
            "pm10": current.get("pm10"),
            "ozone": current.get("ozone"),
            "no2": current.get("nitrogen_dioxide")
        }
    except requests.exceptions.RequestException:
        return None
    except (KeyError, ValueError, TypeError):
        return None


def compare_locations(loc1, loc2):
    result = {
        "location1": None,
        "location2": None,
        "data1": None,
        "data2": None,
        "better": None,
        "message": "",
        "error": None
    }

    lat1, lon1, name1 = get_coords(loc1)
    if lat1 is None:
        result["error"] = f"Location 1: {name1}"
        return result

    lat2, lon2, name2 = get_coords(loc2)
    if lat2 is None:
        result["error"] = f"Location 2: {name2}"
        return result

    result["location1"] = name1
    result["location2"] = name2

    data1 = fetch_current_aq(lat1, lon1)
    data2 = fetch_current_aq(lat2, lon2)

    if data1 is None or data2 is None:
        result["error"] = "Could not fetch air quality for one or both locations."
        return result

    result["data1"] = data1
    result["data2"] = data2

    aqi1 = data1.get("aqi")
    aqi2 = data2.get("aqi")

    if aqi1 is None or aqi2 is None:
        result["message"] = "AQI missing for one location. Compare other values manually."
        return result

    try:
        aqi1_f = float(aqi1)
        aqi2_f = float(aqi2)
    except (TypeError, ValueError):
        result["message"] = "Could not compare AQI values."
        return result

    if aqi1_f < aqi2_f:
        result["better"] = name1
        result["message"] = f"{name1} has cleaner air (AQI {aqi1_f}) than {name2} (AQI {aqi2_f})."
    elif aqi2_f < aqi1_f:
        result["better"] = name2
        result["message"] = f"{name2} has cleaner air (AQI {aqi2_f}) than {name1} (AQI {aqi1_f})."
    else:
        result["better"] = "Equal"
        result["message"] = f"Both locations have similar AQI ({aqi1_f})."

    return result


if __name__ == "__main__":
    print("Testing comparison module...")
    print("Validate 'Lagos':", validate_location_string("Lagos"))
    print("Validate '9.0,7.4':", validate_location_string("9.0,7.4"))
    print("Validate bad:", validate_location_string("@#$"))
    print("Comparing Abuja and Lagos...")
    res = compare_locations("Abuja", "Lagos")
    if res.get("error"):
        print("Error:", res["error"])
    else:
        print("Loc1:", res["location1"], res["data1"])
        print("Loc2:", res["location2"], res["data2"])
        print("Result:", res["message"])
