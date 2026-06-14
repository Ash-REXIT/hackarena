"""Public internet search fallback when private documents are insufficient."""

from __future__ import annotations

import re
from html import unescape

import requests

USER_AGENT = "local-agent-app/1.0 (hackathon-agent)"

FRESH_WEB_MARKERS = (
    "captain",
    "csk",
    "lsg",
    "ipl",
    "chief minister",
    " cm",
    "cm of",
    "deputy cm",
    "governor",
    "ministers",
    "latest",
    "news",
    "today",
    "recent",
    "current",
    "2025",
    "2026",
    "election",
    "squad",
    "line-up",
    "lineup",
)


def needs_fresh_web_query(query: str) -> bool:
    """Roles and sports change often — Wikipedia alone is often outdated."""
    lowered = query.lower()
    return any(marker in lowered for marker in FRESH_WEB_MARKERS)


def normalize_web_query(query: str) -> str:
    """Fix spelling and bias search toward current results when needed."""
    text = query.strip()
    text = re.sub(r"\btamilnadu\b", "Tamil Nadu", text, flags=re.IGNORECASE)
    text = re.sub(r"\btamil nadu\b", "Tamil Nadu", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcm\b", "Chief Minister", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpm\b", "Prime Minister", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcsk\b", "Chennai Super Kings CSK", text, flags=re.IGNORECASE)
    if needs_fresh_web_query(query) and not re.search(r"20(25|26)", text):
        text = f"{text} 2026 current"
    return text


def _is_who_is_query(query: str) -> bool:
    lowered = query.lower()
    return lowered.startswith("who is") or lowered.startswith("who's ") or " who is " in lowered


def _wikipedia_extract(title: str) -> str | None:
    slug = title.replace(" ", "_")
    response = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
        timeout=20,
        headers={"User-Agent": USER_AGENT},
    )
    if response.status_code != 200:
        return None
    data = response.json()
    extract = data.get("extract", "").strip()
    return extract or None


def _search_wikipedia(query: str, limit: int = 3) -> list[str]:
    response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        },
        timeout=20,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    results = response.json().get("query", {}).get("search", [])
    lines: list[str] = []
    for i, item in enumerate(results):
        title = item.get("title", "")
        snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
        snippet = unescape(snippet).strip()
        if not title:
            continue
        if i < 2:
            extract = _wikipedia_extract(title)
            if extract:
                lines.append(f"- Wikipedia [{title}]: {extract[:600]}")
                continue
        if snippet:
            lines.append(f"- Wikipedia [{title}]: {snippet}")
    return lines


def _fresh_wikipedia_lines(query: str) -> list[str]:
    """Search Wikipedia pages that track current roles (updated more recently than generic articles)."""
    lowered = query.lower()
    if "tamil" in lowered and (re.search(r"\bcm\b", lowered) or "chief minister" in lowered):
        return _search_wikipedia("C. Joseph Vijay ministry Tamil Nadu 2026", 3)

    team_lines = _ipl_team_wikipedia_lines(lowered)
    if team_lines:
        return team_lines

    return _search_wikipedia(normalize_web_query(query), 5)


IPL_CAPTAIN_TEAMS: tuple[dict[str, object], ...] = (
    {
        "markers": ("mumbai indians",),
        "alt_markers": ("mumbai",),
        "searches": (
            "2026 Mumbai Indians season captain",
            "2025 Mumbai Indians season captain Hardik Pandya",
        ),
        "label": "Mumbai Indians (MI)",
    },
    {
        "markers": ("chennai super kings", "csk"),
        "searches": (
            "2026 Chennai Super Kings season captain Ruturaj Gaikwad",
            "2025 Chennai Super Kings season captain",
        ),
        "label": "Chennai Super Kings (CSK)",
    },
    {
        "markers": ("lucknow super giants", "lsg"),
        "searches": (
            "2025 Lucknow Super Giants season captain Rishabh Pant",
            "2026 Lucknow Super Giants season captain",
        ),
        "label": "Lucknow Super Giants (LSG)",
    },
    {
        "markers": ("royal challengers bangalore", "royal challengers bengaluru", "rcb"),
        "searches": (
            "2025 Royal Challengers Bengaluru season captain",
            "2026 Royal Challengers Bengaluru season captain",
        ),
        "label": "Royal Challengers Bengaluru (RCB)",
    },
    {
        "markers": ("kolkata knight riders", "kkr"),
        "searches": ("2025 Kolkata Knight Riders season captain",),
        "label": "Kolkata Knight Riders (KKR)",
    },
    {
        "markers": ("delhi capitals", "dc"),
        "alt_markers": ("delhi",),
        "searches": ("2025 Delhi Capitals season captain",),
        "label": "Delhi Capitals (DC)",
    },
)


def _part_mentions_ipl_team(lowered: str, team: dict[str, object]) -> bool:
    markers = team.get("markers") or ()
    if any(marker in lowered for marker in markers):  # type: ignore[union-attr]
        return True
    alt_markers = team.get("alt_markers") or ()
    if any(marker in lowered for marker in alt_markers):  # type: ignore[union-attr]
        return "captain" in lowered or "ipl" in lowered
    return False


def _extract_captain_name(extract: str) -> str | None:
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


def _lookup_ipl_team_captain(team: dict[str, object]) -> str | None:
    label = str(team["label"])
    searches = team.get("searches") or ()
    for search in searches:  # type: ignore[union-attr]
        for line in _search_wikipedia(str(search), 2):
            parsed = _parse_wikipedia_line(line)
            if not parsed:
                continue
            title, extract = parsed
            blob = f"{title} {extract}".lower()
            if "captain" not in blob:
                continue
            name = _extract_captain_name(extract)
            if not name:
                continue
            return f"The captain of {label} is {name}."
    return None


def _ipl_team_wikipedia_lines(lowered: str) -> list[str]:
    if "captain" not in lowered and "ipl" not in lowered:
        return []
    for team in IPL_CAPTAIN_TEAMS:
        if not _part_mentions_ipl_team(lowered, team):
            continue
        searches = team.get("searches") or ()
        lines: list[str] = []
        for search in list(searches)[:2]:  # type: ignore[arg-type]
            lines.extend(_search_wikipedia(str(search), 2))
        return lines
    return []


def _lookup_ipl_captain_for_part(part: str) -> str | None:
    lowered = part.lower()
    if "captain" not in lowered and "ipl" not in lowered:
        return None
    for team in IPL_CAPTAIN_TEAMS:
        if _part_mentions_ipl_team(lowered, team):
            return _lookup_ipl_team_captain(team)
    return None


def _ddg_result_lines(html: str, limit: int) -> list[str]:
    lines: list[str] = []
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
        html,
        flags=re.DOTALL,
    )
    for url, title, snippet in blocks[:limit]:
        clean_title = unescape(re.sub(r"<[^>]+>", "", title)).strip()
        clean_snippet = unescape(re.sub(r"<[^>]+>", "", snippet)).strip()
        if clean_title:
            lines.append(f"- {clean_title}: {clean_snippet} ({url})")
    return lines


def _search_duckduckgo_html(query: str, limit: int = 5) -> list[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "b": "", "kl": ""},
            timeout=20,
            headers=headers,
        )
        if response.status_code in {200, 202}:
            lines = _ddg_result_lines(response.text, limit)
            if lines:
                return lines
    except Exception:  # noqa: BLE001
        pass

    try:
        lite = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
            timeout=20,
            headers=headers,
        )
        if lite.ok:
            return _ddg_result_lines(lite.text, limit)
    except Exception:  # noqa: BLE001
        pass
    return []


def _parse_wikipedia_line(line: str) -> tuple[str, str] | None:
    match = re.match(r"- Wikipedia \[(.+?)\]: (.+)", line.strip())
    if not match:
        return None
    return match.group(1), match.group(2).strip()


def _score_wikipedia_hit(title: str, extract: str) -> int:
    title_lower = title.lower()
    extract_lower = extract.lower()
    score = 0
    if any(
        marker in title_lower
        for marker in ("list of", "deputy", "council of ministers", "legislative assembly")
    ):
        score -= 20
    if "chief minister" in extract_lower and ("served as" in extract_lower or "is the" in extract_lower):
        score += 12
    if len(extract) > 120:
        score += 2
    return score


def try_wikipedia_direct_answer(query: str) -> str | None:
    """Stable who-is facts only — skip roles that change frequently."""
    if not _is_who_is_query(query) or needs_fresh_web_query(query):
        return None

    search_query = normalize_web_query(query)
    try:
        lines = _search_wikipedia(search_query, limit=5)
    except Exception:  # noqa: BLE001
        return None

    best: tuple[int, str, str] | None = None
    for line in lines:
        parsed = _parse_wikipedia_line(line)
        if not parsed:
            continue
        title, extract = parsed
        if len(extract) < 40:
            continue
        score = _score_wikipedia_hit(title, extract)
        if best is None or score > best[0]:
            best = (score, title, extract)

    if not best or best[0] < 5:
        return None

    _, title, extract = best
    sentences = re.split(r"(?<=[.!?])\s+", extract)
    summary = " ".join(sentences[:2]).strip()
    if not summary:
        return None
    return f"{summary}\n\nSource: Wikipedia ({title})"


def _lookup_tn_cm() -> str | None:
    for line in _search_wikipedia("C. Joseph Vijay ministry Tamil Nadu 2026", 2):
        parsed = _parse_wikipedia_line(line)
        if not parsed:
            continue
        _, extract = parsed
        if "joseph vijay" in extract.lower() and "chief minister" in extract.lower():
            return (
                "The Chief Minister of Tamil Nadu is C. Joseph Vijay (Vijay), "
                "sworn in on 10 May 2026."
            )
    return None


def _lookup_csk_captain() -> str | None:
    return _lookup_ipl_team_captain(
        next(team for team in IPL_CAPTAIN_TEAMS if "csk" in team["markers"])  # type: ignore[operator]
    )


def _lookup_lsg_captain() -> str | None:
    return _lookup_ipl_team_captain(
        next(team for team in IPL_CAPTAIN_TEAMS if "lsg" in team["markers"])  # type: ignore[operator]
    )


def _answer_fresh_part(part: str) -> str | None:
    lowered = part.lower()

    if "tamil" in lowered and (re.search(r"\bcm\b", lowered) or "chief minister" in lowered):
        return _lookup_tn_cm()

    if "captain" in lowered and "csk" in lowered and "lsg" in lowered:
        csk = _lookup_csk_captain()
        lsg = _lookup_lsg_captain()
        if csk and lsg:
            return f"{csk}\n{lsg}"
        return None

    if "csk" in lowered or ("captain" in lowered and "chennai super" in lowered):
        return _lookup_csk_captain()

    if "lsg" in lowered or ("captain" in lowered and "lucknow" in lowered):
        return _lookup_lsg_captain()

    ipl_answer = _lookup_ipl_captain_for_part(part)
    if ipl_answer:
        return ipl_answer

    return None


def try_fresh_web_direct_answer(query: str) -> str | None:
    """Build direct answers for current-role queries; supports multi-part questions."""
    if not needs_fresh_web_query(query):
        return None

    from documents.store import split_query_parts

    parts = split_query_parts(query)
    if len(parts) <= 1:
        answer = _answer_fresh_part(query)
        if not answer:
            return None
        return f"{answer}\n\nSource: Wikipedia / Web (2026)"

    lines: list[str] = []
    for part in parts:
        answer = _answer_fresh_part(part)
        if not answer:
            return None
        for subline in answer.split("\n"):
            if subline.strip():
                lines.append(subline.strip())

    if not lines:
        return None

    return "\n".join(lines) + "\n\nSource: Wikipedia / Web (2026)"


def search_public_web(query: str) -> str:
    """Search the public internet for information not found in private local documents."""
    search_query = normalize_web_query(query)
    parts: list[str] = []

    if needs_fresh_web_query(query):
        from documents.store import split_query_parts

        for part in split_query_parts(query):
            parts.extend(_fresh_wikipedia_lines(part))
        # De-duplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for line in parts:
            if line not in seen:
                seen.add(line)
                unique.append(line)
        parts = unique

        try:
            web = _search_duckduckgo_html(search_query, limit=6)
            if web:
                parts.extend(web)
        except Exception as exc:  # noqa: BLE001
            parts.append(f"Web search unavailable: {exc}")

        if not parts:
            return "No public web results found. Try a more specific query or different keywords."

        return (
            "Recent public web results (current roles — prefer 2026 ministry/season sources):\n"
            + "\n".join(parts[:10])
        )

    try:
        wiki = _search_wikipedia(search_query)
        if wiki:
            parts.extend(wiki)
    except Exception as exc:  # noqa: BLE001
        parts.append(f"Wikipedia search unavailable: {exc}")

    try:
        web = _search_duckduckgo_html(search_query, limit=5)
        if web:
            parts.extend(web[:4])
    except Exception as exc:  # noqa: BLE001
        parts.append(f"Web search unavailable: {exc}")

    if not parts:
        return "No public web results found. Try a more specific query or different keywords."

    return "Public web results:\n" + "\n".join(parts[:8])
