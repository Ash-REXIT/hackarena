import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Bot, Loader2, User } from "lucide-react";
import { confidenceColor, privacyColor } from "../../api/client";

function normalizeText(text) {
  return (text || "").replace(/\\n/g, "\n");
}

function renderContent(text) {
  const normalized = normalizeText(text);
  const lines = normalized.split("\n");
  const sourceIdx = lines.findIndex((line) => /^Source:/i.test(line.trim()));

  if (sourceIdx === -1) {
    return normalized;
  }

  const answer = lines.slice(0, sourceIdx).join("\n").trim();
  const source = lines.slice(sourceIdx).join("\n").trim();

  return (
    <>
      <span>{answer}</span>
      {source && (
        <>
          {"\n\n"}
          <span className="text-gray-400 text-xs block pt-1 border-t border-border/50 mt-2">{source}</span>
        </>
      )}
    </>
  );
}
function TypingText({ text }) {
  const normalized = normalizeText(text);

  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    setDisplayed("");
    let i = 0;
    const step = Math.max(1, Math.floor(normalized.length / 80));
    const timer = setInterval(() => {
      i += step;
      setDisplayed(normalized.slice(0, i));
      if (i >= normalized.length) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [normalized]);
  return renderContent(displayed || normalized.slice(0, 1));
}

function MessageBubble({ message, isLatest }) {
  const isUser = message.role === "user";
  const meta = message.meta;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
          isUser ? "bg-accent/20 text-accent" : "bg-surface-elevated text-gray-400"
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div className={`max-w-[85%] space-y-2 ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? "bg-accent/15 border border-accent/25 text-gray-100 rounded-tr-sm"
              : "bg-surface-card border border-border text-gray-200 rounded-tl-sm"
          }`}
        >
          {isUser ? message.content : isLatest ? <TypingText text={message.content} /> : renderContent(message.content)}
        </div>
        {meta && (
          <div className="flex flex-wrap gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full border border-border ${confidenceColor(meta.confidence)}`}>
              Confidence {meta.confidence}%
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full border border-border ${privacyColor(meta.privacy_score)}`}>
              Privacy {meta.privacy_score}
            </span>
            {(meta.primary_source === "local" || meta.primary_source === "hybrid") &&
              meta.documents_used?.map((doc) => (
                <span key={doc} className="text-xs px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                  {doc}
                </span>
              ))}
            {meta.primary_source === "mcp" &&
              (meta.mcp_tools_used?.length ? meta.mcp_tools_used : ["get_current_time"]).map((tool) => (
                <span
                  key={tool}
                  className="text-xs px-2 py-0.5 rounded-full bg-blue-400/10 text-blue-300 border border-blue-400/25"
                >
                  MCP: {tool}
                </span>
              ))}
            {meta.web_used && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-danger/10 text-danger border border-danger/20">
                Web Used
              </span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default function ChatWindow({ messages, loading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-center py-20">
          <Bot className="w-12 h-12 text-accent/40 mb-4" />
          <h2 className="text-lg font-medium mb-2">Ask FoxZilla anything</h2>
          <p className="text-sm text-gray-500 max-w-md">
            Your local documents are searched first. Internet is used only when confidence is low.
          </p>
        </div>
      )}
      {messages.map((msg, i) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          isLatest={i === messages.length - 1 && msg.role === "assistant"}
        />
      ))}
      {loading && (
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Loader2 className="w-4 h-4 animate-spin text-accent" />
          FoxZilla agents working… (local model, usually under ~1 min)
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
