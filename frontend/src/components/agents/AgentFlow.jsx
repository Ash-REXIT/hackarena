import { motion } from "framer-motion";
import { ArrowDown } from "lucide-react";

const STEPS = [
  "Question",
  "Retriever Agent",
  "Confidence Agent",
  "Decision Agent",
  "Local Agent / Web Agent",
  "Answer Agent",
];

export default function AgentFlow({ agents = [] }) {
  const activeIdx = agents.findIndex((a) => a.status === "active");
  const webSkipped = agents.find((a) => a.name === "Web Agent")?.status === "skipped";

  return (
    <div className="card p-6">
      <h3 className="text-sm font-medium text-gray-300 mb-6">Agent Flow Diagram</h3>
      <div className="flex flex-col items-center gap-1">
        {STEPS.map((step, i) => {
          const isActive = i > 0 && i - 1 === activeIdx;
          const isDone = i > 0 && agents[i - 1]?.status === "complete";
          const isBranch = step.includes("/");

          return (
            <div key={step} className="flex flex-col items-center w-full">
              <motion.div
                animate={isActive ? { scale: [1, 1.02, 1] } : {}}
                transition={{ repeat: isActive ? Infinity : 0, duration: 1.5 }}
                className={`px-4 py-2 rounded-lg text-sm text-center w-full max-w-xs border transition-colors ${
                  isActive
                    ? "border-accent bg-accent/10 text-accent"
                    : isDone
                    ? "border-accent/30 bg-accent/5 text-gray-200"
                    : "border-border bg-surface-elevated text-gray-500"
                }`}
              >
                {isBranch && webSkipped ? "Local Agent ✓ · Web Agent ⊘" : step}
              </motion.div>
              {i < STEPS.length - 1 && <ArrowDown className="w-4 h-4 text-gray-600 my-1" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
