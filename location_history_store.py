import json
import os
import re
from datetime import datetime


class LocationHistoryStore:
    def __init__(self, favourites_file="favourites.json", readings_file="readings.json", advisories_file="advisories.json"):
        self.favourites_file = favourites_file
        self.readings_file = readings_file
        self.advisories_file = advisories_file

    def _load_json(self, filepath):
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except (json.JSONDecodeError, OSError, IOError):
            return []

    def _save_json(self, filepath, data):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, IOError, TypeError):
            return False

    def validate_date_input(self, date_str):
        if not date_str:
            return False
        pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, str(date_str).strip()):
            return False
        try:
            datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def add_favourite(self, name, latitude, longitude):
        favourites = self._load_json(self.favourites_file)
        for fav in favourites:
            if fav.get("name") == name:
                return False  # already exists
        favourites.append({
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return self._save_json(self.favourites_file, favourites)

    def get_favourites(self):
        return self._load_json(self.favourites_file)

    def remove_favourite(self, name):
        favourites = self._load_json(self.favourites_file)
        new_list = [f for f in favourites if f.get("name") != name]
        if len(new_list) == len(favourites):
            return False
        return self._save_json(self.favourites_file, new_list)

    def save_reading(self, reading_dict):
        readings = self._load_json(self.readings_file)
        readings.append(reading_dict)
        if len(readings) > 200:
            readings = readings[-200:]
        return self._save_json(self.readings_file, readings)

    def get_readings(self, location_name=None, limit=50):
        readings = self._load_json(self.readings_file)
        if location_name:
            readings = [r for r in readings if r.get("location_name") == location_name]
        return readings[-limit:]

    def save_advisory(self, location_name, advisory_text, aqi=None):
        advisories = self._load_json(self.advisories_file)
        advisories.append({
            "location_name": location_name,
            "advisory": advisory_text,
            "aqi": aqi,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        if len(advisories) > 100:
            advisories = advisories[-100:]
        return self._save_json(self.advisories_file, advisories)

    def get_advisories(self, limit=20):
        advisories = self._load_json(self.advisories_file)
        return advisories[-limit:]


if __name__ == "__main__":
    store = LocationHistoryStore(
        favourites_file="test_favourites.json",
        readings_file="test_readings.json",
        advisories_file="test_advisories.json"
    )
    print("Testing LocationHistoryStore...")
    print("Date valid 2026-11-04:", store.validate_date_input("2026-11-04"))
    print("Date valid bad:", store.validate_date_input("04-11-2026"))
    ok = store.add_favourite("Abuja", 9.08, 7.40)
    print("Add favourite:", ok)
    print("Favourites:", store.get_favourites())
    sample_reading = {
        "location_name": "Abuja",
        "latitude": 9.08,
        "longitude": 7.40,
        "timestamp": "2026-11-04 12:00:00",
        "aqi": 55,
        "pm25": 14.2,
        "pm10": 22.0,
        "ozone": 60,
        "no2": 12
    }
    print("Save reading:", store.save_reading(sample_reading))
    print("Readings:", store.get_readings())
    print("Save advisory:", store.save_advisory("Abuja", "Air is moderate. Limit outdoor time for children.", 55))
    print("Advisories:", store.get_advisories())
    for f in ["test_favourites.json", "test_readings.json", "test_advisories.json"]:
        if os.path.exists(f):
            os.remove(f)
    print("Test files cleaned.")
