"""Public internet search fallback when private documents are insufficient."""

from __future__ import annotations

import re
from html import unescape

import requests

USER_AGENT = "local-agent-app/1.0 (hackathon-agent)"


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


def _search_duckduckgo_html(query: str, limit: int = 5) -> list[str]:
    response = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query, "b": "", "kl": ""},
        timeout=20,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    html = response.text

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


def search_public_web(query: str) -> str:
    """Search the public internet for information not found in private local documents."""
    parts: list[str] = []

    try:
        wiki = _search_wikipedia(query)
        if wiki:
            parts.extend(wiki)
    except Exception as exc:  # noqa: BLE001
        parts.append(f"Wikipedia search unavailable: {exc}")

    try:
        web = _search_duckduckgo_html(query)
        if web:
            parts.extend(web)
    except Exception as exc:  # noqa: BLE001
        parts.append(f"Web search unavailable: {exc}")

    if not parts:
        return (
            "No public web results found. Try a more specific query or different keywords."
        )

    return "Public web results:\n" + "\n".join(parts[:8])
