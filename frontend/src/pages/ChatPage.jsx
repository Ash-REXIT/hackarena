import { useMemo, useState } from "react";
import { useApp } from "../context/AppContext";
import Sidebar from "../components/layout/Sidebar";
import ChatWindow from "../components/chat/ChatWindow";
import ChatInput from "../components/chat/ChatInput";
import EvidenceDrawer from "../components/evidence/EvidenceDrawer";

export default function ChatPage() {
  const { activeConversation, sendMessage, loading, createConversation } = useApp();
  const [lastMeta, setLastMeta] = useState(null);

  const messages = activeConversation?.messages || [];

  const latestMeta = useMemo(() => {
    const last = [...messages].reverse().find((m) => m.role === "assistant" && m.meta);
    return last?.meta || lastMeta;
  }, [messages, lastMeta]);

  const handleSend = async (query) => {
    if (!activeConversation) createConversation();
    const data = await sendMessage(query);
    if (data) setLastMeta(data);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] max-w-[1600px] mx-auto">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 bg-surface">
        <ChatWindow messages={messages} loading={loading} />
        <ChatInput onSend={handleSend} loading={loading} />
      </div>
      <div className="hidden xl:block w-80 shrink-0 border-l border-border p-4 overflow-y-auto bg-surface">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-4">Evidence Panel</h2>
        <EvidenceDrawer meta={latestMeta} />
      </div>
    </div>
  );
}
