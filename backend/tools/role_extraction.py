"""Generic current-role extraction from Wikipedia season/ministry pages."""

from __future__ import annotations

import re
from datetime import datetime

# Alias map: spoken/shorthand → canonical entity name (extend as needed, not per-question).
IPL_TEAM_ALIASES: dict[str, str] = {
    "mumbai indians": "Mumbai Indians",
    "mumbai": "Mumbai Indians",
    "mi": "Mumbai Indians",
    "chennai super kings": "Chennai Super Kings",
    "csk": "Chennai Super Kings",
    "lucknow super giants": "Lucknow Super Giants",
    "lsg": "Lucknow Super Giants",
    "royal challengers bangalore": "Royal Challengers Bengaluru",
    "royal challengers bengaluru": "Royal Challengers Bengaluru",
    "rcb": "Royal Challengers Bengaluru",
    "kolkata knight riders": "Kolkata Knight Riders",
    "kkr": "Kolkata Knight Riders",
    "delhi capitals": "Delhi Capitals",
    "dc": "Delhi Capitals",
    "sunrisers hyderabad": "Sunrisers Hyderabad",
    "srh": "Sunrisers Hyderabad",
    "rajasthan royals": "Rajasthan Royals",
    "rr": "Rajasthan Royals",
    "punjab kings": "Punjab Kings",
    "pbks": "Punjab Kings",
    "gujarat titans": "Gujarat Titans",
    "gt": "Gujarat Titans",
}

STATE_ALIASES: dict[str, str] = {
    "tamil nadu": "Tamil Nadu",
    "tamilnadu": "Tamil Nadu",
    "karnataka": "Karnataka",
    "maharashtra": "Maharashtra",
    "delhi": "Delhi",
    "uttar pradesh": "Uttar Pradesh",
    "west bengal": "West Bengal",
    "kerala": "Kerala",
    "andhra pradesh": "Andhra Pradesh",
    "telangana": "Telangana",
}


def current_years() -> tuple[int, int]:
    year = datetime.now().year
    return year, year - 1


def _detect_ipl_team(text: str) -> str | None:
    lowered = text.lower()
    if "captain" not in lowered and "ipl" not in lowered:
        return None
    # Longest alias first to avoid partial matches.
    for alias in sorted(IPL_TEAM_ALIASES, key=len, reverse=True):
        if alias in lowered:
            return IPL_TEAM_ALIASES[alias]
    return None


def _detect_state(text: str) -> str | None:
    lowered = text.lower()
    if not (re.search(r"\bcm\b", lowered) or "chief minister" in lowered):
        return None
    for alias in sorted(STATE_ALIASES, key=len, reverse=True):
        if alias in lowered:
            return STATE_ALIASES[alias]
    return None


def build_fresh_search_queries(part: str) -> list[str]:
    """Build targeted Wikipedia searches from role + entity patterns."""
    lowered = part.lower()
    year, prev_year = current_years()
    queries: list[str] = []

    team = _detect_ipl_team(part)
    if team:
        queries.extend(
            [
                f"{year} {team} season captain",
                f"{prev_year} {team} season captain",
                f"{team} IPL captain {year}",
            ]
        )

    state = _detect_state(part)
    if state:
        queries.extend(
            [
                f"{year} {state} chief minister ministry",
                f"{prev_year} {state} legislative assembly chief minister",
                f"{state} chief minister {year}",
            ]
        )

    if "ceo" in lowered:
        org = _extract_org_after_of(part, ("ceo", "ceo of"))
        if org:
            queries.append(f"{org} CEO {year}")

    if "president of" in lowered or "president " in lowered:
        org = _extract_org_after_of(part, ("president of", "president"))
        if org:
            queries.append(f"{org} president {year}")

    if not queries and needs_fresh_markers(lowered):
        normalized = re.sub(r"\bcm\b", "Chief Minister", part, flags=re.IGNORECASE)
        queries.append(f"{normalized} {year} current")

    return queries


def needs_fresh_markers(lowered: str) -> bool:
    markers = (
        "captain",
        "ipl",
        "chief minister",
        " cm",
        "governor",
        "latest",
        "current",
        "minister",
        "ceo",
        "president",
    )
    return any(marker in lowered for marker in markers)


def _extract_org_after_of(text: str, prefixes: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    for prefix in prefixes:
        idx = lowered.find(prefix)
        if idx == -1:
            continue
        rest = text[idx + len(prefix) :].strip(" ?.,;")
        if rest:
            return rest.split("?")[0].strip()[:80]
    return None


def extract_captain_name(extract: str) -> str | None:
    patterns = (
        r"(?:was |is )captained by ([A-Z][A-Za-z .'-]+?)(?:\s+and|\s+with|\.|,|$)",
        r"([A-Z][A-Za-z .'-]+?) was appointed as the captain",
        r"([A-Z][A-Za-z .'-]+?) was named captain",
        r"appointed ([A-Z][A-Za-z .'-]+?) as (?:the )?captain",
    )
    for pattern in patterns:
        match = re.search(pattern, extract)
        if match:
            name = match.group(1).strip()
            if 1 <= len(name.split()) <= 4:
                return name
    return None


def extract_chief_minister_name(extract: str) -> str | None:
    patterns = (
        r"([A-Z][A-Za-z .'-]+?) (?:is |was )(?:the )?(?:\d+(?:st|nd|rd|th) )?Chief Minister",
        r"Chief Minister(?:ial)?(?: ministry|ship)?[^.]{0,120}?([A-Z][A-Za-z .'-]+?)(?:\.|,| sworn|$)",
        r"sworn in as Chief Minister[^.]{0,60}?([A-Z][A-Za-z .'-]+)",
        r"([A-Z][A-Za-z .'-]+?), (?:popularly )?known as",
    )
    for pattern in patterns:
        match = re.search(pattern, extract)
        if match:
            name = match.group(1).strip()
            if 1 <= len(name.split()) <= 5 and name.lower() not in {"the", "a", "an"}:
                return name
    return None


def entity_in_text(entity: str, text: str) -> bool:
    """Loose check that the Wikipedia extract is about the requested entity."""
    blob = text.lower()
    entity_lower = entity.lower()
    if entity_lower in blob:
        return True
    # Team abbreviations / partial (e.g. "Mumbai Indians" → "mumbai")
    first_word = entity_lower.split()[0]
    return len(first_word) > 4 and first_word in blob


def try_extract_role_answer(part: str, wiki_lines: list[str]) -> str | None:
    """Parse role-holder from pre-fetched Wikipedia lines."""
    team = _detect_ipl_team(part)
    state = _detect_state(part)

    for line in wiki_lines:
        match = re.match(r"- Wikipedia \[(.+?)\]: (.+)", line.strip())
        if not match:
            continue
        title, extract = match.group(1), match.group(2).strip()
        blob = f"{title} {extract}"

        if team:
            if "captain" not in blob.lower():
                continue
            if not entity_in_text(team, blob) and "season" not in title.lower():
                continue
            name = extract_captain_name(extract)
            if name:
                return f"The captain of {team} is {name}."

        if state:
            if "chief minister" not in blob.lower():
                continue
            if not entity_in_text(state, blob):
                continue
            name = extract_chief_minister_name(extract)
            if name:
                return f"The Chief Minister of {state} is {name}."

    return None
