import re
from datetime import datetime


class HealthRiskAnalyzer:
    def __init__(self):
        self.aqi_levels = [
            (0, 50, "Good"),
            (51, 100, "Moderate"),
            (101, 150, "Unhealthy for Sensitive Groups"),
            (151, 200, "Unhealthy"),
            (201, 300, "Very Unhealthy"),
            (301, 500, "Hazardous")
        ]

    def get_aqi_category(self, aqi):
        if aqi is None:
            return "Unknown"
        try:
            aqi_val = float(aqi)
        except (TypeError, ValueError):
            return "Unknown"
        for low, high, name in self.aqi_levels:
            if low <= aqi_val <= high:
                return name
        if aqi_val > 500:
            return "Hazardous"
        return "Unknown"

    def is_outdoor_safe(self, aqi, pm25=None):
        category = self.get_aqi_category(aqi)
        if category in ("Good", "Moderate"):
            return True, "Outdoor activity is generally safe for most people."
        if category == "Unhealthy for Sensitive Groups":
            return False, "Sensitive groups (children, elderly, asthma) should limit outdoor activity."
        if category in ("Unhealthy", "Very Unhealthy", "Hazardous"):
            return False, "Avoid outdoor activity. Stay indoors if possible."
        return False, "Unable to determine safety due to missing data."

    def recommend_cleanest_time(self, hourly_data, after_time=None):
        if not hourly_data or "time" not in hourly_data:
            return None, "No hourly data available."

        times = hourly_data.get("time", [])
        aqi_list = hourly_data.get("us_aqi") or hourly_data.get("european_aqi") or []
        pm25_list = hourly_data.get("pm2_5") or []

        if not times:
            return None, "No time data."

        best_index = None
        best_value = None

        values = aqi_list if aqi_list else pm25_list
        if not values:
            return None, "No pollutant values in forecast."

        for i, val in enumerate(values):
            if val is None:
                continue
            if after_time and i < len(times) and times[i] < after_time:
                continue
            try:
                num = float(val)
            except (TypeError, ValueError):
                continue
            if best_value is None or num < best_value:
                best_value = num
                best_index = i

        if best_index is None or best_index >= len(times):
            return None, "Could not find cleanest hour."

        clean_time = times[best_index]
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", str(clean_time)):
            pass
        return clean_time, f"Cleanest time around {clean_time} (value: {best_value})"

    def basic_protective_advice(self, aqi):
        category = self.get_aqi_category(aqi)
        advice = []
        if category == "Good":
            advice.append("Air is good. Open windows for fresh air.")
            advice.append("No mask needed for most people.")
        elif category == "Moderate":
            advice.append("Sensitive people may want to limit long outdoor time.")
            advice.append("You can open windows for short periods.")
        elif category == "Unhealthy for Sensitive Groups":
            advice.append("Children, elderly and people with asthma should reduce outdoor time.")
            advice.append("Consider a mask (N95/KN95) if you must go outside.")
            advice.append("Keep windows closed during peak pollution.")
        else:
            advice.append("Stay indoors as much as possible.")
            advice.append("Wear a well-fitting mask (N95/KN95) if you go outside.")
            advice.append("Keep windows closed. Use fan or air purifier if available.")
        return advice

    def group_risk_notes(self, aqi):
        category = self.get_aqi_category(aqi)
        notes = {
            "children": "",
            "elderly": "",
            "asthma": "",
            "respiratory": ""
        }
        if category in ("Good", "Moderate"):
            notes["children"] = "Usually fine for outdoor play."
            notes["elderly"] = "Normal outdoor activity is okay."
            notes["asthma"] = "Most people with asthma can continue usual activities."
            notes["respiratory"] = "Low extra risk for most respiratory conditions."
        elif category == "Unhealthy for Sensitive Groups":
            notes["children"] = "Limit long outdoor play, especially active games."
            notes["elderly"] = "Reduce time outside, especially if you have heart or lung issues."
            notes["asthma"] = "Carry inhaler. Avoid heavy exercise outdoors."
            notes["respiratory"] = "People with COPD or similar should stay indoors more."
        else:
            notes["children"] = "Avoid outdoor play. Keep them indoors."
            notes["elderly"] = "Stay indoors. High risk of breathing problems."
            notes["asthma"] = "High risk of attacks. Stay inside and follow action plan."
            notes["respiratory"] = "High risk. Stay indoors and rest."
        return notes


if __name__ == "__main__":
    analyzer = HealthRiskAnalyzer()
    print("Testing HealthRiskAnalyzer...")
    print("AQI 45 category:", analyzer.get_aqi_category(45))
    print("AQI 120 category:", analyzer.get_aqi_category(120))
    safe, msg = analyzer.is_outdoor_safe(45)
    print("Outdoor safe (45):", safe, msg)
    safe, msg = analyzer.is_outdoor_safe(160)
    print("Outdoor safe (160):", safe, msg)
    print("Protective advice for AQI 110:")
    for line in analyzer.basic_protective_advice(110):
        print(" -", line)
    notes = analyzer.group_risk_notes(180)
    print("Group notes (asthma):", notes["asthma"])
    sample_hourly = {
        "time": ["2026-11-04T08:00", "2026-11-04T14:00", "2026-11-04T20:00"],
        "us_aqi": [55, 90, 40],
        "pm2_5": [15, 30, 12]
    }
    t, msg = analyzer.recommend_cleanest_time(sample_hourly)
    print("Cleanest time:", t, msg)
    t, msg = analyzer.recommend_cleanest_time(sample_hourly, after_time="2026-11-04T12:00")
    print("Cleanest time after 12:00:", t, msg)
