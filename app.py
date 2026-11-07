import streamlit as st
import os
from datetime import datetime

from air_quality_client import AirQualityClient
from air_reading import AirReading
from health_risk_analyzer import HealthRiskAnalyzer
from location_history_store import LocationHistoryStore
from gemini_advisor import generate_health_explanation, get_gemini_api_key
from comparison import compare_locations

st.set_page_config(page_title="Air Quality & Pollution Health Advisor", layout="wide")
st.title("Air Quality & Pollution Health Advisor")

client = AirQualityClient()
analyzer = HealthRiskAnalyzer()
store = LocationHistoryStore(
    favourites_file="favourites.json",
    readings_file="readings.json",
    advisories_file="advisories.json"
)

st.sidebar.header("Settings")
api_key_input = st.sidebar.text_input("Gemini API Key", type="password",
                                      value=os.environ.get("GEMINI_API_KEY", ""),
                                      help="Needed for AI health explanations")
if api_key_input:
    os.environ["GEMINI_API_KEY"] = api_key_input

st.sidebar.markdown("---")
st.sidebar.subheader("Favourite Locations")
favourites = store.get_favourites()
if favourites:
    for fav in favourites:
        cols = st.sidebar.columns([3, 1])
        cols[0].write(fav.get("name", "?"))
        if cols[1].button("X", key=f"del_{fav.get('name')}"):
            store.remove_favourite(fav.get("name"))
            st.rerun()
else:
    st.sidebar.write("No favourites yet.")

tab1, tab2, tab3 = st.tabs(["Check Air Quality", "Compare Two Locations", "History & Trends"])

with tab1:
    st.subheader("Current & Forecast Air Quality")
    location_input = st.text_input("Enter location (city name or lat,lon)", placeholder="Abuja or 9.08,7.40")
    col_btn1, col_btn2 = st.columns(2)
    get_clicked = col_btn1.button("Get Air Quality", type="primary")
    save_fav_clicked = col_btn2.button("Save as Favourite")

    if save_fav_clicked and location_input:
        lat, lon, name = client.get_coordinates(location_input)
        if lat is not None:
            if store.add_favourite(name, lat, lon):
                st.success(f"Saved {name} to favourites")
            else:
                st.info("Already in favourites")
        else:
            st.error(client.last_error or "Could not resolve location")

    if get_clicked:
        if not location_input or not client.validate_location_input(location_input):
            st.error("Please enter a valid location (city name or latitude,longitude).")
        else:
            with st.spinner("Fetching air quality data..."):
                lat, lon, display_name = client.get_coordinates(location_input)
                if lat is None:
                    st.error(client.last_error or "Location not found")
                else:
                    data = client.fetch_air_quality(lat, lon, forecast_days=3)
                    if data is None:
                        st.error(client.last_error or "Failed to fetch air quality")
                    else:
                        current = data.get("current", {})
                        reading = AirReading(display_name, lat, lon)
                        reading.set_from_api_data(current)

                        if reading.has_missing_data():
                            st.warning("Some pollutant data is missing for this location.")

                        st.markdown(f"### {display_name}")
                        st.caption(f"Updated: {reading.timestamp}")

                        c1, c2, c3, c4, c5 = st.columns(5)
                        aqi_cat = analyzer.get_aqi_category(reading.aqi)
                        c1.metric("AQI", f"{reading.aqi if reading.aqi is not None else 'N/A'}", aqi_cat)
                        c2.metric("PM2.5", f"{reading.pm25 if reading.pm25 is not None else 'N/A'} µg/m³")
                        c3.metric("PM10", f"{reading.pm10 if reading.pm10 is not None else 'N/A'} µg/m³")
                        c4.metric("Ozone", f"{reading.ozone if reading.ozone is not None else 'N/A'} µg/m³")
                        c5.metric("NO₂", f"{reading.no2 if reading.no2 is not None else 'N/A'} µg/m³")

                        safe, safe_msg = analyzer.is_outdoor_safe(reading.aqi, reading.pm25)
                        if safe:
                            st.success(safe_msg)
                        else:
                            st.warning(safe_msg)

                        hourly = data.get("hourly", {})
                        clean_time, clean_msg = analyzer.recommend_cleanest_time(hourly, after_time=current.get("time"))
                        if clean_time:
                            st.info(f"Recommended cleaner time to go outside: **{clean_time}**")
                        else:
                            st.write(clean_msg)

                        st.subheader("Protective advice")
                        for tip in analyzer.basic_protective_advice(reading.aqi):
                            st.write(f"- {tip}")

                        notes = analyzer.group_risk_notes(reading.aqi)
                        with st.expander("Quick notes for sensitive groups"):
                            st.write(f"**Children:** {notes['children']}")
                            st.write(f"**Elderly:** {notes['elderly']}")
                            st.write(f"**Asthma:** {notes['asthma']}")
                            st.write(f"**Other respiratory conditions:** {notes['respiratory']}")

                        st.subheader("AI health explanation")
                        if get_gemini_api_key() or api_key_input:
                            with st.spinner("Generating explanation..."):
                                explanation = generate_health_explanation(
                                    display_name,
                                    reading.aqi,
                                    reading.pm25,
                                    reading.pm10,
                                    reading.ozone,
                                    reading.no2,
                                    aqi_cat,
                                    api_key=api_key_input or get_gemini_api_key()
                                )
                                st.write(explanation)
                                store.save_advisory(display_name, explanation, reading.aqi)
                        else:
                            st.info("Enter a Gemini API key in the sidebar to get AI explanations for children, elderly, asthma and other respiratory conditions.")

                        st.subheader("Forecast (next hours)")
                        times = hourly.get("time", [])[:24]
                        aqi_h = hourly.get("us_aqi") or hourly.get("european_aqi") or []
                        pm25_h = hourly.get("pm2_5") or []
                        if times:
                            rows = []
                            for i, t in enumerate(times):
                                aqi_val = aqi_h[i] if i < len(aqi_h) else None
                                pm_val = pm25_h[i] if i < len(pm25_h) else None
                                rows.append({"Time": t, "AQI": aqi_val, "PM2.5": pm_val})
                            st.dataframe(rows, use_container_width=True)

                        store.save_reading(reading.to_dict())
                        st.caption("Reading saved to local history.")

with tab2:
    st.subheader("Compare air quality between two locations")
    col_a, col_b = st.columns(2)
    loc1 = col_a.text_input("Location 1", placeholder="Abuja")
    loc2 = col_b.text_input("Location 2", placeholder="Lagos")
    if st.button("Compare", key="cmp_btn"):
        if not loc1 or not loc2:
            st.error("Enter both locations.")
        else:
            with st.spinner("Comparing..."):
                res = compare_locations(loc1, loc2)
                if res.get("error"):
                    st.error(res["error"])
                else:
                    st.success(res.get("message", ""))
                    d1 = res.get("data1") or {}
                    d2 = res.get("data2") or {}
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**{res.get('location1')}**")
                        st.write(f"AQI: {d1.get('aqi')}")
                        st.write(f"PM2.5: {d1.get('pm25')}")
                        st.write(f"PM10: {d1.get('pm10')}")
                        st.write(f"Ozone: {d1.get('ozone')}")
                        st.write(f"NO2: {d1.get('no2')}")
                    with c2:
                        st.markdown(f"**{res.get('location2')}**")
                        st.write(f"AQI: {d2.get('aqi')}")
                        st.write(f"PM2.5: {d2.get('pm25')}")
                        st.write(f"PM10: {d2.get('pm10')}")
                        st.write(f"Ozone: {d2.get('ozone')}")
                        st.write(f"NO2: {d2.get('no2')}")

with tab3:
    st.subheader("Previous readings")
    all_readings = store.get_readings(limit=200)
    names = ["All locations"]
    for r in all_readings:
        name = r.get("location_name")
        if name and name not in names:
            names.append(name)
    col1, col2 = st.columns(2)
    chosen = col1.selectbox("Location", names)
    date_text = col2.text_input("Filter by date (YYYY-MM-DD, optional)", placeholder="2026-11-04")

    readings = []
    for r in all_readings:
        if chosen == "All locations" or r.get("location_name") == chosen:
            readings.append(r)

    if date_text.strip():
        if store.validate_date_input(date_text):
            filtered = []
            for r in readings:
                if str(r.get("timestamp", "")).startswith(date_text.strip()):
                    filtered.append(r)
            readings = filtered
        else:
            st.error("Invalid date. Use the format YYYY-MM-DD, for example 2026-11-04.")
            readings = []

    if readings:
        aqi_values = []
        for r in readings:
            if r.get("aqi") is not None:
                aqi_values.append(r.get("aqi"))
        if chosen == "All locations":
            st.caption("Choose a location to see its AQI trend chart.")
        elif len(aqi_values) >= 2:
            st.markdown("**AQI trend over time**")
            st.line_chart({"AQI": aqi_values})
        else:
            st.caption("Save at least 2 readings for this location to see a trend chart.")
        for r in reversed(readings[-30:]):
            st.write(f"{r.get('timestamp', '')} | **{r.get('location_name', '')}** | AQI {r.get('aqi')} | PM2.5 {r.get('pm25')}")
    else:
        st.write("No readings found. Check a location first.")

    st.subheader("Saved advisories")
    advisories = store.get_advisories(limit=10)
    if advisories:
        for a in reversed(advisories):
            with st.expander(f"{a.get('created_at')} - {a.get('location_name')} (AQI {a.get('aqi')})"):
                st.write(a.get("advisory", ""))
    else:
        st.write("No advisories saved yet.")

st.markdown("---")
st.caption("Data: Open-Meteo Air Quality API | AI explanations: Gemini")
