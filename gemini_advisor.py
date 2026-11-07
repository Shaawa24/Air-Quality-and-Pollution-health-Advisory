import os
import re
import requests


def get_gemini_api_key():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return key


def call_gemini(prompt, api_key=None):
    if not api_key:
        api_key = get_gemini_api_key()
    if not api_key:
        return "Gemini API key not set. Set GEMINI_API_KEY environment variable or enter key in the app."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return "No response from Gemini."
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return "Empty response from Gemini."
        text = parts[0].get("text", "")
        return text.strip() if text else "Empty text from Gemini."
    except requests.exceptions.Timeout:
        return "Gemini request timed out."
    except requests.exceptions.HTTPError as e:
        return f"Gemini HTTP error: {e}"
    except requests.exceptions.RequestException as e:
        return f"Gemini network error: {str(e)}"
    except (KeyError, ValueError, TypeError, IndexError):
        return "Failed to parse Gemini response."


def build_health_prompt(location, aqi, pm25, pm10, ozone, no2, category):
    prompt = f"""You are a helpful air quality advisor. Explain the following measurements in simple everyday language for ordinary people.

Location: {location}
AQI: {aqi} ({category})
PM2.5: {pm25} ug/m3
PM10: {pm10} ug/m3
Ozone: {ozone} ug/m3
Nitrogen dioxide (NO2): {no2} ug/m3

Explain what these numbers mean for:
1. Children
2. Elderly people
3. People with asthma
4. People with other respiratory conditions

Also give short practical advice on:
- Whether outdoor activity is safe
- Best simple protective steps (masks, windows, indoor air)

Keep the whole answer short, clear and easy to understand. Do not use medical jargon. Do not give medical diagnoses."""
    return prompt


def generate_health_explanation(location, aqi, pm25, pm10, ozone, no2, category, api_key=None):
    prompt = build_health_prompt(location, aqi, pm25, pm10, ozone, no2, category)
    return call_gemini(prompt, api_key)


def extract_pollutant_numbers(text):
    numbers = re.findall(r"\d+\.?\d*", text)
    return [float(n) for n in numbers]


if __name__ == "__main__":
    print("Testing Gemini advisor module...")
    print("API key present:", bool(get_gemini_api_key()))
    sample_prompt = build_health_prompt("Abuja", 55, 14, 22, 60, 12, "Moderate")
    print("Prompt length:", len(sample_prompt))
    print("Sample numbers from text:", extract_pollutant_numbers("AQI 55, PM2.5 is 14.2"))
    if get_gemini_api_key():
        result = generate_health_explanation("Abuja", 55, 14, 22, 60, 12, "Moderate")
        print("Gemini reply (first 300 chars):")
        print(result[:300] if result else "No result")
    else:
        print("Skipping live Gemini call (no API key). Module is ready.")
        print("Fallback message:", call_gemini("test"))
