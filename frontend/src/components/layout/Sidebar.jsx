import { MessageSquarePlus } from "lucide-react";
import { useApp } from "../../context/AppContext";
import { privacyColor } from "../../api/client";

export default function Sidebar() {
  const {
    conversations,
    activeChatId,
    setActiveChatId,
    createConversation,
    documents,
    analyticsSummary,
  } = useApp();

  return (
    <aside className="w-64 shrink-0 border-r border-border bg-surface-card flex flex-col h-[calc(100vh-3.5rem)]">
      <div className="p-4 border-b border-border">
        <button type="button" onClick={createConversation} className="btn-primary w-full text-sm">
          <MessageSquarePlus className="w-4 h-4" /> New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="text-xs uppercase tracking-wider text-gray-500 px-2 mb-2">Recent Chats</div>
        {conversations.length === 0 && (
          <p className="text-xs text-gray-500 px-2">No conversations yet</p>
        )}
        {conversations.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => setActiveChatId(c.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate transition-colors ${
              activeChatId === c.id
                ? "bg-accent/10 text-accent border border-accent/20"
                : "text-gray-400 hover:bg-surface-elevated hover:text-gray-200"
            }`}
          >
            {c.title}
          </button>
        ))}
      </div>

      <div className="p-4 border-t border-border space-y-3 text-xs">
        <div>
          <div className="text-gray-500 mb-1">Knowledge Summary</div>
          <div className="text-gray-300">{documents.length} documents indexed</div>
        </div>
        <div>
          <div className="text-gray-500 mb-1">Privacy Average</div>
          <div className={`font-semibold text-lg ${privacyColor(analyticsSummary.avgPrivacy)}`}>
            {analyticsSummary.total ? analyticsSummary.avgPrivacy : "—"}
          </div>
        </div>
      </div>
    </aside>
  );
}
