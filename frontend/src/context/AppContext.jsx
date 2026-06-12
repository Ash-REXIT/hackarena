import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const STORAGE_KEY = "foxzilla_state_v2";

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveState(partial) {
  const current = loadState();
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...current, ...partial }));
}

const defaultSettings = {
  temperature: 0.1,
  topK: 4,
  chunkSize: 512,
  internetFallback: true,
  theme: "dark",
};

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const persisted = loadState();
  const [health, setHealth] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [conversations, setConversations] = useState(persisted.conversations || []);
  const [activeChatId, setActiveChatId] = useState(persisted.activeChatId || null);
  const [analytics, setAnalytics] = useState(persisted.analytics || []);
  const [lastAgentRun, setLastAgentRun] = useState(persisted.lastAgentRun || null);
  const [settings, setSettings] = useState({ ...defaultSettings, ...persisted.settings });
  const [loading, setLoading] = useState(false);

  const refreshHealth = useCallback(async () => {
    try {
      const data = await api.health();
      setHealth(data);
    } catch {
      setHealth(null);
    }
  }, []);

  const refreshDocuments = useCallback(async () => {
    try {
      const data = await api.documents();
      setDocuments(data.documents || []);
    } catch {
      setDocuments([]);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    refreshDocuments();
    const interval = setInterval(refreshHealth, 30000);
    return () => clearInterval(interval);
  }, [refreshHealth, refreshDocuments]);

  useEffect(() => {
    saveState({ conversations, activeChatId, analytics, lastAgentRun, settings });
  }, [conversations, activeChatId, analytics, lastAgentRun, settings]);

  const activeConversation = useMemo(
    () => conversations.find((c) => c.id === activeChatId) || null,
    [conversations, activeChatId]
  );

  const createConversation = useCallback(() => {
    const id = crypto.randomUUID();
    const conv = { id, title: "New chat", messages: [], createdAt: Date.now() };
    setConversations((prev) => [conv, ...prev]);
    setActiveChatId(id);
    return id;
  }, []);

  const sendMessage = useCallback(
    async (query, chatId = activeChatId) => {
      let id = chatId;
      if (!id) id = createConversation();

      const userMsg = { id: crypto.randomUUID(), role: "user", content: query, ts: Date.now() };
      setConversations((prev) =>
        prev.map((c) =>
          c.id === id
            ? {
                ...c,
                title: c.messages.length ? c.title : query.slice(0, 48),
                messages: [...c.messages, userMsg],
              }
            : c
        )
      );

      setLoading(true);
      try {
        const data = await api.chat(query);
        const assistantMsg = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.response,
          meta: data,
          ts: Date.now(),
        };

        setConversations((prev) =>
          prev.map((c) =>
            c.id === id ? { ...c, messages: [...c.messages, assistantMsg] } : c
          )
        );

        const point = {
          id: crypto.randomUUID(),
          ts: Date.now(),
          query,
          confidence: data.confidence,
          privacy: data.privacy_score,
          webUsed: data.web_used,
          localPct: data.source_breakdown?.local_documents ?? 0,
          webPct: data.source_breakdown?.web_verification ?? 0,
        };
        setAnalytics((prev) => [...prev.slice(-49), point]);
        setLastAgentRun(data);
        return data;
      } finally {
        setLoading(false);
      }
    },
    [activeChatId, createConversation]
  );

  const uploadDocument = useCallback(
    async (file) => {
      await api.upload(file);
      await refreshDocuments();
    },
    [refreshDocuments]
  );

  const analyticsSummary = useMemo(() => {
    if (!analytics.length) {
      return { avgPrivacy: 100, avgConfidence: 0, saved: health?.internet_budget?.internet_requests_saved ?? 50, total: 0 };
    }
    const avgPrivacy = Math.round(analytics.reduce((s, a) => s + a.privacy, 0) / analytics.length);
    const avgConfidence = Math.round(analytics.reduce((s, a) => s + a.confidence, 0) / analytics.length);
    const saved = health?.internet_budget?.internet_requests_saved ?? 50;
    return { avgPrivacy, avgConfidence, saved, total: analytics.length };
  }, [analytics, health]);

  const value = {
    health,
    documents,
    conversations,
    activeChatId,
    activeConversation,
    analytics,
    analyticsSummary,
    lastAgentRun,
    settings,
    loading,
    setActiveChatId,
    createConversation,
    sendMessage,
    uploadDocument,
    refreshHealth,
    refreshDocuments,
    setSettings,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
