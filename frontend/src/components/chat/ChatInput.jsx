import { useState } from "react";
import { Send } from "lucide-react";

const DEMO_QUERIES = [
  "How many leave days do employees get?",
  "Latest Mozilla AI news",
  "What time is it in Tokyo?",
];

export default function ChatInput({ onSend, loading }) {
  const [value, setValue] = useState("");

  const submit = (e) => {
    e.preventDefault();
    const q = value.trim();
    if (!q || loading) return;
    onSend(q);
    setValue("");
  };

  return (
    <div className="border-t border-border bg-surface-card p-4">
      <div className="flex flex-wrap gap-2 mb-3">
        {DEMO_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => setValue(q)}
            className="text-xs px-3 py-1 rounded-full border border-border text-gray-400 hover:border-accent/40 hover:text-accent transition-colors"
          >
            {q.length > 32 ? `${q.slice(0, 32)}…` : q}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="flex gap-3">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(e);
            }
          }}
          rows={2}
          placeholder="Ask anything — local docs searched first…"
          className="flex-1 resize-none rounded-xl border border-border bg-surface px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-accent/50"
        />
        <button type="submit" disabled={loading || !value.trim()} className="btn-primary self-end px-4">
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
