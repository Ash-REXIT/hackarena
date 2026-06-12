/** Normalize agent run payloads from /api/chat for UI + storage. */

export function normalizeAgentRun(run) {
  if (!run || typeof run !== "object") return null;

  const timeline = Array.isArray(run.timeline)
    ? run.timeline.map((step) => ({
        time: step?.time ?? "",
        event: step?.event ?? "",
        agent: step?.agent ?? "",
      }))
    : [];

  const agents = Array.isArray(run.agents)
    ? run.agents.map((agent) => ({
        name: agent?.name ?? "Agent",
        status: agent?.status ?? "pending",
        detail: agent?.detail ?? "",
      }))
    : [];

  return {
    ...run,
    timeline,
    agents,
  };
}

/** Keep a small snapshot for localStorage so timeline/agents are always persisted. */
export function summarizeAgentRunForStorage(run) {
  const normalized = normalizeAgentRun(run);
  if (!normalized) return null;

  return {
    agents: normalized.agents,
    timeline: normalized.timeline,
    confidence: normalized.confidence ?? 0,
    privacy_score: normalized.privacy_score ?? 100,
    primary_source: normalized.primary_source ?? "local",
    web_used: normalized.web_used ?? false,
    source_breakdown: normalized.source_breakdown ?? {},
    knowledge_boundary: normalized.knowledge_boundary ?? null,
    mcp_tools_used: normalized.mcp_tools_used ?? [],
    updated_at: Date.now(),
  };
}

/** Prefer the newest assistant message meta, then fall back to lastAgentRun. */
export function findLatestAgentRun(conversations = [], fallback = null) {
  let best = normalizeAgentRun(fallback);
  let bestTs = best?.updated_at ?? 0;

  for (const conv of conversations) {
    for (const msg of conv.messages || []) {
      if (msg.role !== "assistant" || !msg.meta) continue;
      const run = normalizeAgentRun(msg.meta);
      if (!run) continue;
      const ts = msg.ts ?? 0;
      if (ts >= bestTs) {
        best = run;
        bestTs = ts;
      }
    }
  }

  return best;
}
