import { motion } from "framer-motion";
import { Clock, FileText, Globe, Shield, Zap } from "lucide-react";
import { confidenceColor, privacyColor } from "../../api/client";

function EvidenceCard({ item }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      className="card p-4 space-y-2"
    >
      <div className="flex items-center gap-2 text-sm font-medium text-accent">
        <FileText className="w-4 h-4" />
        {item.document}
      </div>
      <blockquote className="text-sm text-gray-300 border-l-2 border-accent/50 pl-3 italic">
        &ldquo;{item.excerpt}&rdquo;
      </blockquote>
      <div className="flex flex-wrap gap-2 text-xs text-gray-500">
        <span className="px-2 py-0.5 rounded bg-surface-elevated">Similarity: {item.score}%</span>
        <span className="px-2 py-0.5 rounded bg-surface-elevated">{item.search_method}</span>
        <span className="px-2 py-0.5 rounded bg-surface-elevated">{item.freshness}</span>
      </div>
    </motion.div>
  );
}

function ToolEvidenceCard({ item }) {
  const args = item.args ? JSON.stringify(item.args) : "";
  return (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      className="card p-4 space-y-2 border-blue-400/30 bg-blue-400/5"
    >
      <div className="flex items-center gap-2 text-sm font-medium text-blue-300">
        <Zap className="w-4 h-4" />
        MCPD · {item.tool}
      </div>
      {args && (
        <div className="text-xs text-gray-500 font-mono break-all">Args: {args}</div>
      )}
      <blockquote className="text-sm text-gray-300 border-l-2 border-blue-400/50 pl-3">
        {item.output || "Tool executed successfully."}
      </blockquote>
      <div className="flex flex-wrap gap-2 text-xs text-gray-500">
        <span className="px-2 py-0.5 rounded bg-surface-elevated flex items-center gap-1">
          <Clock className="w-3 h-3" /> Live data
        </span>
        <span className="px-2 py-0.5 rounded bg-surface-elevated">Source: MCP</span>
      </div>
    </motion.div>
  );
}

export default function EvidenceDrawer({ meta }) {
  if (!meta) {
    return (
      <div className="card p-6 h-full flex flex-col items-center justify-center text-center text-gray-500">
        <Shield className="w-10 h-10 mb-3 opacity-40" />
        <p className="text-sm">Evidence appears here after you ask a question.</p>
      </div>
    );
  }

  const isMcp = meta.primary_source === "mcp" || (meta.tool_evidence?.length > 0 && meta.primary_source !== "hybrid");
  const isHybrid = meta.primary_source === "hybrid";
  const toolEvidence = meta.tool_evidence || [];
  const docEvidence = meta.evidence || [];

  return (
    <div className="space-y-4 h-full overflow-y-auto">
      <div className="card p-4">
        <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-3">Answer Metrics</h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-gray-500">Confidence</div>
            <div className={`text-2xl font-bold ${confidenceColor(meta.confidence)}`}>{meta.confidence}%</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Privacy</div>
            <div className={`text-2xl font-bold ${privacyColor(meta.privacy_score)}`}>{meta.privacy_score}</div>
          </div>
        </div>
        {meta.source_breakdown && (
          <div className="mt-3 pt-3 border-t border-border text-xs space-y-1 text-gray-400">
            {meta.source_breakdown.local_documents > 0 && (
              <div>{meta.source_breakdown.local_documents}% Local Documents</div>
            )}
            {meta.source_breakdown.web_verification > 0 && (
              <div>{meta.source_breakdown.web_verification}% Web Verification</div>
            )}
            {meta.source_breakdown.mcp_tools > 0 && (
              <div>{meta.source_breakdown.mcp_tools}% MCP Tools</div>
            )}
          </div>
        )}
      </div>

      {meta.knowledge_boundary && (
        <div
          className={`card p-4 text-sm ${
            meta.knowledge_boundary.status === "mcp_live"
              ? "border-blue-400/30"
              : meta.knowledge_boundary.status === "found_locally"
              ? "border-accent/30"
              : "border-warn/30"
          }`}
        >
          <div className="font-medium mb-1">{meta.knowledge_boundary.label}</div>
          <p className="text-gray-400 text-xs">{meta.knowledge_boundary.message}</p>
        </div>
      )}

      {isMcp && (
        <div>
          <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-3 flex items-center gap-1">
            <Zap className="w-3 h-3" /> Tool Evidence
          </h3>
          <div className="space-y-3">
            {toolEvidence.length ? (
              toolEvidence.map((item, i) => (
                <ToolEvidenceCard key={`${item.tool}-${i}`} item={item} />
              ))
            ) : (
              <ToolEvidenceCard
                item={{
                  tool: meta.mcp_tools_used?.[0] || "get_current_time",
                  args: {},
                  output: "MCPD time tool used for this answer.",
                }}
              />
            )}
          </div>
        </div>
      )}

      {(isHybrid || (!isMcp && docEvidence.length > 0)) && (
        <div>
          <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-3">Document Evidence</h3>
          <div className="space-y-3">
            {docEvidence.length ? (
              docEvidence.map((item) => <EvidenceCard key={item.chunk_id} item={item} />)
            ) : (
              <p className="text-sm text-gray-500">No local document evidence.</p>
            )}
          </div>
        </div>
      )}

      {!isMcp && !isHybrid && docEvidence.length === 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-3">Document Evidence</h3>
          <p className="text-sm text-gray-500">No local document evidence.</p>
        </div>
      )}

      {meta.internet_sources?.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-3 flex items-center gap-1">
            <Globe className="w-3 h-3" /> Web Sources
          </h3>
          <div className="space-y-2">
            {meta.internet_sources.map((s, i) => (
              <div key={i} className="card p-3 text-xs text-gray-400 truncate">
                {s.name}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
