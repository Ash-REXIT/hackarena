const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const queryEl = document.getElementById("query");
const sendBtn = document.getElementById("send-btn");
const healthEl = document.getElementById("health");
const docsListEl = document.getElementById("docs-list");
const fileInput = document.getElementById("file-input");
const uploadZone = document.getElementById("upload-zone");
const uploadStatus = document.getElementById("upload-status");
const browseBtn = document.getElementById("browse-btn");
const startChatBtn = document.getElementById("start-chat-btn");
const scrollUploadBtn = document.getElementById("scroll-upload-btn");

const privacyScoreEl = document.getElementById("privacy-score");
const privacyReasonEl = document.getElementById("privacy-reason");
const confidenceBarEl = document.getElementById("confidence-bar");
const confidenceValueEl = document.getElementById("confidence-value");
const boundaryStatusEl = document.getElementById("boundary-status");
const agentFlowEl = document.getElementById("agent-flow");
const budgetUsedEl = document.getElementById("budget-used");
const budgetLimitEl = document.getElementById("budget-limit");
const budgetSavedEl = document.getElementById("budget-saved");
const sourceBreakdownEl = document.getElementById("source-breakdown");
const explainReasonEl = document.getElementById("explain-reason");
const evidencePanelEl = document.getElementById("evidence-panel");
const timelinePanelEl = document.getElementById("timeline-panel");
const sourcesPanelEl = document.getElementById("sources-panel");
const mozillaStackEl = document.getElementById("mozilla-stack");

function addMessage(text, role, extraClass = "") {
  const div = document.createElement("div");
  div.className = `message ${role} ${extraClass}`.trim();
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

async function fetchJson(url, options = {}, timeoutMs = 600000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      ...options,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Request failed");
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timed out. The local model may still be thinking.");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function confidenceColor(value) {
  if (value >= 75) return "green";
  if (value >= 45) return "yellow";
  return "red";
}

function privacyColor(score) {
  if (score >= 90) return "high";
  if (score >= 60) return "medium";
  return "low";
}

function resetPanels() {
  privacyScoreEl.textContent = "…";
  privacyScoreEl.className = "privacy-score";
  privacyReasonEl.textContent = "Analyzing…";
  confidenceBarEl.style.width = "0%";
  confidenceBarEl.className = "confidence-bar";
  confidenceValueEl.textContent = "…";
  boundaryStatusEl.innerHTML = '<span class="boundary-loading">Analyzing local knowledge…</span>';
  sourceBreakdownEl.textContent = "…";
  explainReasonEl.textContent = "";
}

function renderIntelligencePanels(data) {
  const privacy = data.privacy_score ?? 100;
  privacyScoreEl.textContent = `${privacy} / 100`;
  privacyScoreEl.className = `privacy-score ${privacyColor(privacy)}`;
  privacyReasonEl.textContent = data.privacy_reason || "";

  const confidence = data.confidence ?? 0;
  confidenceBarEl.style.width = `${confidence}%`;
  confidenceBarEl.className = `confidence-bar ${confidenceColor(confidence)}`;
  confidenceValueEl.textContent = `${confidence}%`;

  const boundary = data.knowledge_boundary;
  if (boundary) {
    const icon = boundary.status === "found_locally" ? "✓" : "⚠";
    const cls = boundary.status === "found_locally" ? "found" : "missing";
    boundaryStatusEl.innerHTML = `
      <div class="boundary ${cls}">
        <span class="boundary-icon">${icon}</span>
        <div>
          <strong>${boundary.label}</strong>
          <p>${boundary.message}</p>
        </div>
      </div>`;
  }

  if (data.agents?.length) {
    agentFlowEl.innerHTML = data.agents
      .map(
        (agent) =>
          `<div class="agent-step ${agent.status}" title="${agent.detail || ""}">
            ${agent.name} ${agent.status === "complete" ? "✓" : agent.status === "skipped" ? "⊘" : agent.status === "active" ? "●" : ""}
          </div>`
      )
      .join("");
  }

  const budget = data.internet_budget;
  if (budget) {
    budgetUsedEl.textContent = budget.internet_requests_used;
    budgetLimitEl.textContent = budget.internet_requests_limit;
    budgetSavedEl.textContent = budget.internet_requests_saved;
  }

  const breakdown = data.source_breakdown || data.explainability?.answer_source;
  if (breakdown) {
    const parts = [];
    if (breakdown.local_documents) parts.push(`${breakdown.local_documents}% Local Documents`);
    if (breakdown.web_verification) parts.push(`${breakdown.web_verification}% Web Verification`);
    if (breakdown.mcp_tools) parts.push(`${breakdown.mcp_tools}% MCP Tools`);
    sourceBreakdownEl.innerHTML = parts.map((p) => `<div class="source-line">${p}</div>`).join("");
  }

  if (data.explainability?.reason) {
    explainReasonEl.textContent = `Reason: ${data.explainability.reason}`;
  }

  if (data.evidence?.length) {
    evidencePanelEl.innerHTML = data.evidence
      .map(
        (item) => `
        <div class="evidence-item">
          <div class="evidence-doc">✓ ${item.document} <span class="freshness">${item.freshness}</span></div>
          <blockquote>"${item.excerpt}"</blockquote>
          <div class="evidence-meta">${item.score}% match · ${item.search_method}</div>
        </div>`
      )
      .join("");
  } else {
    evidencePanelEl.innerHTML = '<p class="muted">No local document evidence for this query.</p>';
  }

  if (data.timeline?.length) {
    timelinePanelEl.innerHTML = data.timeline
      .map(
        (step) => `
        <div class="timeline-item">
          <span class="timeline-time">${step.time}</span>
          <span class="timeline-event">${step.event}</span>
          <span class="timeline-agent">${step.agent}</span>
        </div>`
      )
      .join("");
  }

  const localSources = data.local_sources || [];
  const internetSources = data.internet_sources || [];
  let sourcesHtml = "";
  if (localSources.length) {
    sourcesHtml += localSources.map((s) => `<div class="source-tag local">📄 ${s.name}</div>`).join("");
  }
  if (internetSources.length) {
    sourcesHtml += internetSources.map((s) => `<div class="source-tag web">🌐 ${s.name.slice(0, 60)}</div>`).join("");
  }
  if (data.mcp_tools_used?.length) {
    sourcesHtml += data.mcp_tools_used.map((t) => `<div class="source-tag mcp">⚡ MCP: ${t}</div>`).join("");
  }
  sourcesPanelEl.innerHTML = sourcesHtml || '<p class="muted">No sources yet.</p>';

  if (data.encoderfile?.message) {
    const enc = data.encoderfile;
    const stackNote = document.getElementById("encoder-live-note");
    if (stackNote) {
      stackNote.innerHTML = `
        <strong>Last query:</strong> ${enc.message}<br>
        <span class="muted">Mode: ${enc.retrieval_mode || "keyword"} · Model: ${enc.model_id || enc.model_type || "encoderfile"}</span>`;
    }
  }
}

function renderAnswerMeta(data) {
  const wrapper = document.createElement("div");
  wrapper.className = "answer-meta";

  const badges = document.createElement("div");
  badges.className = "meta-badges";

  if (data.confidence != null) {
    const b = document.createElement("span");
    b.className = `meta-badge confidence-${confidenceColor(data.confidence)}`;
    b.textContent = `Confidence ${data.confidence}%`;
    badges.appendChild(b);
  }

  if (data.privacy_score != null) {
    const b = document.createElement("span");
    b.className = `meta-badge privacy-${privacyColor(data.privacy_score)}`;
    b.textContent = `Privacy ${data.privacy_score}/100`;
    badges.appendChild(b);
  }

  if (data.web_used) {
    const b = document.createElement("span");
    b.className = "meta-badge web";
    b.textContent = "Web Used";
    badges.appendChild(b);
  } else if (data.knowledge_boundary?.status === "found_locally") {
    const b = document.createElement("span");
    b.className = "meta-badge local";
    b.textContent = "Local Only";
    badges.appendChild(b);
  }

  if (data.mcp_tools_used?.length) {
    for (const tool of data.mcp_tools_used) {
      const b = document.createElement("span");
      b.className = "meta-badge mcp";
      b.textContent = `MCP: ${tool}`;
      badges.appendChild(b);
    }
  }

  wrapper.appendChild(badges);
  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function loadDocuments() {
  try {
    const data = await fetchJson("/api/documents");
    if (!data.documents?.length) {
      docsListEl.innerHTML = '<p class="muted">No documents yet. Upload files above.</p>';
      return;
    }
    docsListEl.innerHTML = data.documents
      .map(
        (doc) => `
        <div class="doc-item">
          <span class="doc-name">📄 ${doc.name}</span>
          <span class="doc-fresh">${doc.freshness_label}</span>
        </div>`
      )
      .join("");
  } catch (error) {
    docsListEl.textContent = `Could not load documents: ${error.message}`;
  }
}

async function loadHealth() {
  try {
    const data = await fetchJson("/api/health");
    const llm = data.llm.ok ? "LLM ✓" : "LLM ✗";
    const encoder = data.encoderfile?.ok ? "Encoder ✓" : "Encoder ✗";
    const mcpd = data.mcpd.ok ? "MCPD ✓" : "MCPD ✗";
    healthEl.textContent = `${llm} · ${encoder} · ${mcpd}`;
    healthEl.className = data.llm.ok && data.mcpd.ok ? "health-pill ok" : "health-pill bad";

    renderMozillaStack(data);

    if (data.internet_budget) {
      budgetUsedEl.textContent = data.internet_budget.internet_requests_used;
      budgetLimitEl.textContent = data.internet_budget.internet_requests_limit;
      budgetSavedEl.textContent = data.internet_budget.internet_requests_saved;
    }
  } catch (error) {
    healthEl.textContent = `Health check failed`;
    healthEl.className = "health-pill bad";
  }
}

function renderMozillaStack(health) {
  const enc = health.encoderfile || {};
  const retrieval = enc.retrieval || {};
  const model = enc.model || {};
  mozillaStackEl.innerHTML = `
    <div class="stack-item ${health.llm?.ok ? "ok" : "bad"}">
      <span class="stack-name">Llamafile</span>
      <span class="stack-detail">${health.llm?.ok ? "Generation · :8080" : "Offline"}</span>
    </div>
    <div class="stack-item ${enc.ok ? "ok" : "bad"}">
      <span class="stack-name">Encoderfile</span>
      <span class="stack-detail">${enc.ok ? (model.model_id || model.model_type || "Online · :8081") : "Offline"}</span>
    </div>
    <div class="stack-item ${health.mcpd?.ok ? "ok" : "bad"}">
      <span class="stack-name">MCPD</span>
      <span class="stack-detail">${health.mcpd?.ok ? "Tools · :8090" : "Offline"}</span>
    </div>
    <div class="stack-item ok">
      <span class="stack-name">Any-Agent</span>
      <span class="stack-detail">Multi-agent orchestration</span>
    </div>
    <div id="encoder-live-note" class="encoder-note">
      ${retrieval.message || "Encoderfile powers retrieval when embedding model is loaded."}
    </div>`;
}

async function uploadFile(file) {
  uploadStatus.textContent = `Uploading ${file.name}…`;
  uploadStatus.className = "upload-status loading";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/documents/upload", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Upload failed");
    uploadStatus.textContent = data.message || "Uploaded successfully.";
    uploadStatus.className = "upload-status success";
    await loadDocuments();
  } catch (error) {
    uploadStatus.textContent = error.message;
    uploadStatus.className = "upload-status error";
  }
}

async function sendQuery(query) {
  addMessage(query, "user");
  sendBtn.disabled = true;
  resetPanels();
  const loadingEl = addMessage("PrivateLens agents working… (local model may take 1–3 min)", "meta");

  try {
    const data = await fetchJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    loadingEl.remove();
    addMessage(data.response || "(empty response)", "assistant");
    renderAnswerMeta(data);
    renderIntelligencePanels(data);
  } catch (error) {
    loadingEl.remove();
    addMessage(`Error: ${error.message}`, "meta");
  } finally {
    sendBtn.disabled = false;
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryEl.value.trim();
  if (!query) return;
  queryEl.value = "";
  await sendQuery(query);
});

document.querySelectorAll(".demo-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const query = chip.dataset.query;
    queryEl.value = query;
    document.getElementById("chat-section").scrollIntoView({ behavior: "smooth" });
  });
});

startChatBtn.addEventListener("click", () => {
  document.getElementById("chat-section").scrollIntoView({ behavior: "smooth" });
  queryEl.focus();
});

scrollUploadBtn.addEventListener("click", () => {
  document.getElementById("upload-section").scrollIntoView({ behavior: "smooth" });
});

browseBtn.addEventListener("click", () => fileInput.click());
uploadZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  if (fileInput.files?.[0]) uploadFile(fileInput.files[0]);
});

uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  if (e.dataTransfer.files?.[0]) uploadFile(e.dataTransfer.files[0]);
});

loadHealth();
loadDocuments();
