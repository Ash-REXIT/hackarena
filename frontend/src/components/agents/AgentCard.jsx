import { motion } from "framer-motion";
import { CheckCircle2, Circle, MinusCircle, Loader2 } from "lucide-react";

const statusIcon = {
  complete: CheckCircle2,
  active: Loader2,
  skipped: MinusCircle,
  pending: Circle,
};

const statusColor = {
  complete: "text-accent border-accent/30 bg-accent/5",
  active: "text-blue-400 border-blue-400/30 bg-blue-400/5",
  skipped: "text-gray-500 border-border bg-surface-elevated opacity-60",
  pending: "text-gray-600 border-border bg-surface-elevated opacity-40",
};

export default function AgentCard({ agent, index }) {
  const Icon = statusIcon[agent.status] || Circle;
  const colors = statusColor[agent.status] || statusColor.pending;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className={`card p-4 border ${colors}`}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">{agent.name}</h3>
        <Icon className={`w-5 h-5 ${agent.status === "active" ? "animate-spin" : ""}`} />
      </div>
      <div className="text-xs text-gray-400 space-y-1">
        <div>Status: <span className="capitalize text-gray-300">{agent.status}</span></div>
        {agent.detail && <div>{agent.detail}</div>}
      </div>
    </motion.div>
  );
}
