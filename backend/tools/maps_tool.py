"""Geocoding helper using OpenStreetMap Nominatim (no API key required)."""

from __future__ import annotations

import requests


def geocode_location(query: str) -> str:
    """Look up latitude and longitude for a place name or address."""
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 3},
        timeout=20,
        headers={"User-Agent": "local-agent-app/1.0"},
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return f"No locations found for '{query}'."

    lines = []
    for item in results:
        lines.append(
            f"{item.get('display_name')} -> lat={item.get('lat')}, lon={item.get('lon')}"
        )
    return "\n".join(lines)
