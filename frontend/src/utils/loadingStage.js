export const LOADING_STAGE_LABELS = {
  retrieval: "Searching local documents…",
  decision: "Decision Agent evaluating…",
  local: "Preparing local evidence…",
  web: "Searching the web…",
  answer_agent: "Answer Agent thinking (local LLM)…",
  finalize: "Finalizing response…",
  done: "Answer ready",
};

export function loadingStageLabel(stage) {
  if (!stage) return "FoxZilla agents working…";
  return LOADING_STAGE_LABELS[stage] || "FoxZilla agents working…";
}
