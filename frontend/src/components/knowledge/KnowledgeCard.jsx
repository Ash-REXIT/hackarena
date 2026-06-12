import { FileText } from "lucide-react";
import { formatDate } from "../../api/client";

export default function KnowledgeCard({ doc, retrievalMode }) {
  return (
    <div className="card p-5 hover:border-accent/30 transition-colors">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
          <FileText className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-100">{doc.name}</h3>
          <p className="text-xs text-gray-500">{doc.freshness_label}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs mb-4">
        <div className="bg-surface-elevated rounded-lg p-2">
          <div className="text-gray-500">Chunks</div>
          <div className="text-gray-200 font-medium">Auto-indexed</div>
        </div>
        <div className="bg-surface-elevated rounded-lg p-2">
          <div className="text-gray-500">Embedding</div>
          <div className="text-accent font-medium">{retrievalMode === "semantic" ? "Semantic" : "Keyword"}</div>
        </div>
      </div>
      <div className="text-xs text-gray-500 mb-3">Updated {formatDate(doc.modified_at)}</div>
      <button type="button" className="btn-secondary w-full text-xs py-2">
        Preview
      </button>
    </div>
  );
}
