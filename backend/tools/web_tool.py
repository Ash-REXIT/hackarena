"""Public internet search fallback when private documents are insufficient."""

from __future__ import annotations

import re
import time
from datetime import datetime
from html import unescape

import requests

from tools.role_extraction import (
    build_fresh_search_queries,
    try_extract_role_answer,
)

USER_AGENT = "FoxZilla/2.0 (local-first-agent)"

FRESH_WEB_MARKERS = (
    "captain",
    "csk",
    "lsg",
    "mi ",
    "ipl",
    "chief minister",
    " cm",
    "cm of",
    "deputy cm",
    "governor",
    "ministers",
    "ceo",
    "president",
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
    """Roles and sports change often — generic Wikipedia pages are often outdated."""
    lowered = query.lower()
    return any(marker in lowered for marker in FRESH_WEB_MARKERS)


def normalize_web_query(query: str) -> str:
    """Fix spelling and bias search toward current results when needed."""
    text = query.strip()
    text = re.sub(r"\btamilnadu\b", "Tamil Nadu", text, flags=re.IGNORECASE)
    text = re.sub(r"\btamil nadu\b", "Tamil Nadu", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcm\b", "Chief Minister", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpm\b", "Prime Minister", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcsk\b", "Chennai Super Kings", text, flags=re.IGNORECASE)
    text = re.sub(r"\blsg\b", "Lucknow Super Giants", text, flags=re.IGNORECASE)
    text = re.sub(r"\brcb\b", "Royal Challengers Bengaluru", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmi\b", "Mumbai Indians", text, flags=re.IGNORECASE)
    year = datetime.now().year
    if needs_fresh_web_query(query) and not re.search(r"20\d{2}", text):
        text = f"{text} {year} current"
    return text


def _is_who_is_query(query: str) -> bool:
    lowered = query.lower()
    return lowered.startswith("who is") or lowered.startswith("who's ") or " who is " in lowered


def _wikipedia_extract(title: str) -> str | None:
    slug = title.replace(" ", "_")
    try:
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
    except Exception:  # noqa: BLE001
        return None


def _search_wikipedia(query: str, limit: int = 3) -> list[str]:
    response = None
    for attempt in range(3):
        try:
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
            if response.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            response.raise_for_status()
            break
        except Exception:  # noqa: BLE001
            if attempt == 2:
                return []
            time.sleep(1.0)
    else:
        return []

    if response is None:
        return []

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


def _fresh_wikipedia_lines(part: str) -> list[str]:
    """Target season/ministry pages via dynamically built queries."""
    lines: list[str] = []
    seen: set[str] = set()
    for search in build_fresh_search_queries(part):
        for line in _search_wikipedia(search, limit=2):
            if line not in seen:
                seen.add(line)
                lines.append(line)
        if len(lines) >= 6:
            break
    if lines:
        return lines
    return _search_wikipedia(normalize_web_query(part), 5)


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


def _score_wikipedia_hit(title: str, extract: str, query: str) -> int:
    title_lower = title.lower()
    extract_lower = extract.lower()
    query_lower = query.lower()
    score = 0
    if any(
        marker in title_lower
        for marker in ("list of", "deputy", "council of ministers", "legislative assembly")
    ):
        score -= 20
    if "season" in title_lower and ("captain" in query_lower or "ipl" in query_lower):
        score += 15
    if "chief minister" in extract_lower and entity_overlap(query_lower, extract_lower):
        score += 12
    if len(extract) > 120:
        score += 2
    return score


def entity_overlap(query_lower: str, text_lower: str) -> bool:
    tokens = [
        t
        for t in re.findall(r"[a-z]{4,}", query_lower)
        if t not in {"who", "what", "latest", "current", "team"}
    ]
    return any(token in text_lower for token in tokens[:6])


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
        score = _score_wikipedia_hit(title, extract, query)
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


def _answer_fresh_part(part: str) -> str | None:
    """Generic role extraction from Wikipedia season/ministry pages."""
    wiki_lines: list[str] = []
    for search in build_fresh_search_queries(part):
        wiki_lines.extend(_search_wikipedia(search, limit=2))
    if not wiki_lines:
        wiki_lines = _fresh_wikipedia_lines(part)
    return try_extract_role_answer(part, wiki_lines)


def try_fresh_web_direct_answer(query: str) -> str | None:
    """Extract current-role answers from Wikipedia; supports multi-part questions."""
    if not needs_fresh_web_query(query):
        return None

    from documents.store import split_query_parts

    parts = split_query_parts(query)
    year = datetime.now().year

    if len(parts) <= 1:
        answer = _answer_fresh_part(query)
        if not answer:
            return None
        return f"{answer}\n\nSource: Wikipedia ({year})"

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

    return "\n".join(lines) + f"\n\nSource: Wikipedia ({year})"


def search_public_web(query: str) -> str:
    """Search the public internet for information not found in private local documents."""
    search_query = normalize_web_query(query)
    parts: list[str] = []
    year = datetime.now().year

    if needs_fresh_web_query(query):
        from documents.store import split_query_parts

        for part in split_query_parts(query):
            parts.extend(_fresh_wikipedia_lines(part))
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
            f"Recent public web results (prefer {year} season/ministry sources):\n"
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
