"""Problem-specific configuration for PrivateLens AI."""

PROBLEM_INSTRUCTIONS = """
PrivateLens AI workflow (multi-agent pipeline already executed before you respond):

1. Retriever Agent — searched local documents (results provided below).
2. Confidence Agent — scored local match quality.
3. Decision Agent — decided whether internet search was needed.
4. Local/Web Agents — gathered evidence (provided below).
5. You are the Answer Agent — synthesize the final response.

Rules:
- Answer from provided local evidence when confidence is high.
- If web evidence is provided, use it for verification or when local docs are insufficient.
- For time/timezone questions, call get_current_time MCP tool.
- Cite document filenames when using local evidence.
- State whether the answer came from local documents, web verification, or MCP tools.
- Do not hallucinate. If evidence is insufficient, say so clearly.
""".strip()

PROBLEM_TOOLS: list[str] = [
    "search_private_documents",
    "list_private_documents",
    "search_public_web",
]
