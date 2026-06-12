import { motion } from "framer-motion";

export default function AgentTimeline({ timeline = [] }) {
  if (!timeline.length) {
    return (
      <div className="card p-8 text-center text-gray-500 text-sm">
        Run a query in Chat to see the agent timeline.
      </div>
    );
  }

  return (
    <div className="card p-4 space-y-0">
      {timeline.map((step, i) => (
        <motion.div
          key={`${step.time}-${i}`}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.03 }}
          className="flex gap-4 py-3 border-b border-border/50 last:border-0"
        >
          <span className="text-xs font-mono text-accent shrink-0 w-16">{step.time}</span>
          <div>
            <div className="text-sm text-gray-200">{step.event}</div>
            <div className="text-xs text-gray-500">{step.agent}</div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
