import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, startTransition } from "react";
import { flushSync } from "react-dom";
import { api } from "../api/client";
import {
  findLatestAgentRun,
  normalizeAgentRun,
  slimConversationsForStorage,
  summarizeAgentRunForStorage,
} from "../utils/agentRun";
import { loadingStageLabel } from "../utils/loadingStage";

const STORAGE_KEY = "foxzilla_state_v2";

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveState(partial) {
  try {
    const current = loadState();
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...current, ...partial }));
  } catch {
    // Ignore quota errors; in-memory state still works for the session.
  }
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
  const [lastAgentRun, setLastAgentRun] = useState(
    () => summarizeAgentRunForStorage(normalizeAgentRun(persisted.lastAgentRun)) || null
  );
  const [settings, setSettings] = useState({ ...defaultSettings, ...persisted.settings });
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const saveTimerRef = useRef(null);
  const [, bumpRender] = useState(0);

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
    if (loading) return undefined;
    refreshHealth();
    refreshDocuments();
    api.settings()
      .then((data) => {
        if (data?.settings) {
          setSettings((prev) => ({ ...prev, ...data.settings }));
        }
      })
      .catch(() => {});
    const interval = setInterval(() => {
      if (!loading) refreshHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, [refreshHealth, refreshDocuments, loading]);

  useEffect(() => {
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }
    saveTimerRef.current = setTimeout(() => {
      saveState({
        conversations: slimConversationsForStorage(conversations),
        activeChatId,
        analytics,
        lastAgentRun,
        settings,
      });
    }, 500);
    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
    };
  }, [conversations, activeChatId, analytics, lastAgentRun, settings]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        bumpRender((n) => n + 1);
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, []);

  useEffect(() => {
    const repaired = findLatestAgentRun(conversations, lastAgentRun);
    if (
      repaired &&
      repaired.timeline?.length > 0 &&
      !(lastAgentRun?.timeline?.length > 0)
    ) {
      setLastAgentRun(summarizeAgentRunForStorage(repaired));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const latestAgentRun = useMemo(
    () => findLatestAgentRun(conversations, lastAgentRun),
    [conversations, lastAgentRun]
  );

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

  const applyChatResult = useCallback((data, id, query) => {
    const assistantMsg = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: data.response,
      meta: data,
      ts: Date.now(),
    };

    flushSync(() => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === id ? { ...c, messages: [...c.messages, assistantMsg] } : c
        )
      );
      setLoading(false);
      setLoadingStage("");
    });

    startTransition(() => {
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
      setLastAgentRun(summarizeAgentRunForStorage(data));
    });
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
      setLoadingStage("retrieval");
      const requestId = crypto.randomUUID();
      const sentAt = Date.now();
      const appliedRef = { current: false };
      const pollMs = 350;
      const pollId = setInterval(async () => {
        try {
          const status = await api.chatStatus();
          if (status.stage && status.request_id === requestId) {
            setLoadingStage(status.stage);
          }
          const matchesRequest =
            status.request_id === requestId ||
            ((status.updated_at || 0) * 1000 >= sentAt - 100 && status.query === query);
          if (
            status.status === "complete" &&
            status.result &&
            matchesRequest &&
            !appliedRef.current
          ) {
            appliedRef.current = true;
            applyChatResult(status.result, id, query);
          }
          if (status.status === "error" && status.error && status.request_id === requestId) {
            setLoadingStage("failed");
          }
        } catch {
          // Ignore transient poll errors while the main request runs.
        }
      }, pollMs);

      try {
        const data = await api.chat(query, requestId);
        if (!appliedRef.current) {
          appliedRef.current = true;
          applyChatResult(data, id, query);
        }

        if (document.hidden && typeof Notification !== "undefined") {
          if (Notification.permission === "granted") {
            new Notification("FoxZilla", { body: "Your answer is ready." });
          } else if (Notification.permission !== "denied") {
            Notification.requestPermission();
          }
        }

        return data;
      } catch (error) {
        setLoading(false);
        setLoadingStage("");
        throw error;
      } finally {
        clearInterval(pollId);
      }
    },
    [activeChatId, applyChatResult, createConversation]
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
    latestAgentRun,
    settings,
    loading,
    loadingStage,
    loadingStageLabel,
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
