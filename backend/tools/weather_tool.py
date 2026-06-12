"""Simple weather lookup using wttr.in (no API key required)."""

from __future__ import annotations

import requests


def get_weather(location: str) -> str:
    """Get a short weather report for a city or place name."""
    response = requests.get(
        f"https://wttr.in/{location}",
        params={"format": "j1"},
        timeout=20,
        headers={"User-Agent": "local-agent-app/1.0"},
    )
    response.raise_for_status()
    data = response.json()

    current = data["current_condition"][0]
    area = data["nearest_area"][0]
    place = area["areaName"][0]["value"]
    country = area["country"][0]["value"]
    temp_c = current["temp_C"]
    feels_like = current["FeelsLikeC"]
    humidity = current["humidity"]
    weather = current["weatherDesc"][0]["value"]

    return (
        f"Weather in {place}, {country}: {weather}. "
        f"Temperature {temp_c}C (feels like {feels_like}C), humidity {humidity}%."
    )
