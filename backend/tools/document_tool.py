"""Search private local documents before using the public internet."""

from __future__ import annotations

from documents.store import list_documents, search_documents


def search_private_documents(query: str) -> str:
    """Search the user's private local document library and return the best matching excerpts."""
    matches = search_documents(query)
    if not matches:
        available = list_documents()
        if not available:
            return "No private documents found. Add files to the private_docs folder."
        return (
            "No relevant private document matches found for that query. "
            f"Available files: {', '.join(available)}. "
            "Consider search_public_web only if the answer is not in local docs."
        )

    lines = ["Private document matches:"]
    for index, match in enumerate(matches, start=1):
        lines.append(f"{index}. [{match.source}] (score {match.score:.2f})")
        lines.append(match.text)
    return "\n".join(lines)


def list_private_documents() -> str:
    """List all private document files available for local search."""
    files = list_documents()
    if not files:
        return "No private documents found in private_docs/."
    return "Private documents:\n" + "\n".join(f"- {name}" for name in files)
