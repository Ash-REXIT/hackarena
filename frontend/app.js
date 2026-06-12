const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const queryEl = document.getElementById("query");
const sendBtn = document.getElementById("send-btn");
const healthEl = document.getElementById("health");
const toolsListEl = document.getElementById("tools-list");
const mcpdSelectEl = document.getElementById("mcpd-tool-select");
const localSelectEl = document.getElementById("local-tool-select");
const refreshToolsBtn = document.getElementById("refresh-tools");
const addMcpdBtn = document.getElementById("add-mcpd-tool");
const addLocalBtn = document.getElementById("add-local-tool");

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

async function loadHealth() {
  try {
    const data = await fetchJson("/api/health");
    const llm = data.llm.ok ? "LLM OK" : "LLM down";
    const mcpd = data.mcpd.ok ? "MCPD OK" : "MCPD down";
    healthEl.textContent = `${llm} | ${mcpd} | ${data.model_id}`;
    healthEl.className = data.llm.ok && data.mcpd.ok ? "health ok" : "health bad";
  } catch (error) {
    healthEl.textContent = `Health check failed: ${error.message}`;
    healthEl.className = "health bad";
  }
}

function renderTools(data) {
  toolsListEl.innerHTML = "";
  for (const tool of data.active_tools) {
    const card = document.createElement("div");
    card.className = `tool-card${tool.enabled ? "" : " disabled"}`;

    const title = tool.type === "mcpd" ? `${tool.server}/${tool.name}` : tool.name;
    card.innerHTML = `
      <h4>${title}</h4>
      <p>${tool.description || "No description"}</p>
      <div class="tool-actions">
        <button type="button" data-action="toggle" data-id="${tool.id}" data-enabled="${tool.enabled}">
          ${tool.enabled ? "Disable" : "Enable"}
        </button>
        <button type="button" class="danger" data-action="remove" data-id="${tool.id}">Remove</button>
      </div>
    `;
    toolsListEl.appendChild(card);
  }

  mcpdSelectEl.innerHTML = "";
  for (const item of data.mcpd_catalog) {
    const option = document.createElement("option");
    option.value = JSON.stringify({ server: item.server, tool: item.name });
    option.textContent = `${item.server}/${item.name}`;
    mcpdSelectEl.appendChild(option);
  }

  localSelectEl.innerHTML = "";
  for (const name of data.available_local_tools) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    localSelectEl.appendChild(option);
  }
}

async function loadTools() {
  const data = await fetchJson("/api/tools");
  renderTools(data);
}

toolsListEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;

  const toolId = button.dataset.id;
  const action = button.dataset.action;

  try {
    if (action === "remove") {
      await fetchJson(`/api/tools/${encodeURIComponent(toolId)}`, { method: "DELETE" });
    }
    if (action === "toggle") {
      const enabled = button.dataset.enabled !== "true";
      await fetchJson(`/api/tools/${encodeURIComponent(toolId)}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      });
    }
    await loadTools();
  } catch (error) {
    addMessage(error.message, "meta");
  }
});

addMcpdBtn.addEventListener("click", async () => {
  if (!mcpdSelectEl.value) return;
  const payload = JSON.parse(mcpdSelectEl.value);
  try {
    await fetchJson("/api/tools/mcpd", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await loadTools();
  } catch (error) {
    addMessage(error.message, "meta");
  }
});

addLocalBtn.addEventListener("click", async () => {
  if (!localSelectEl.value) return;
  try {
    await fetchJson("/api/tools/local", {
      method: "POST",
      body: JSON.stringify({ name: localSelectEl.value }),
    });
    await loadTools();
  } catch (error) {
    addMessage(error.message, "meta");
  }
});

refreshToolsBtn.addEventListener("click", loadTools);

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryEl.value.trim();
  if (!query) return;

  addMessage(query, "user");
  queryEl.value = "";
  sendBtn.disabled = true;

  try {
    const data = await fetchJson("/api/chat", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
    addMessage(data.response || "(empty response)", "assistant");
    if (data.tools_used?.length) {
      addMessage(`Tools used: ${data.tools_used.join(", ")}`, "meta");
    }
  } catch (error) {
    addMessage(`Error: ${error.message}`, "meta");
  } finally {
    sendBtn.disabled = false;
  }
});

loadHealth();
loadTools();
