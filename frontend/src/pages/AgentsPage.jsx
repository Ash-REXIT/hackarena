import { Link } from "react-router-dom";
import { useApp } from "../context/AppContext";
import AgentCard from "../components/agents/AgentCard";
import AgentFlow from "../components/agents/AgentFlow";
import AgentTimeline from "../components/agents/AgentTimeline";

const DEFAULT_AGENTS = [
  { name: "Retriever Agent", status: "pending", detail: "Waiting" },
  { name: "Confidence Agent", status: "pending", detail: "Waiting" },
  { name: "Decision Agent", status: "pending", detail: "Waiting" },
  { name: "Local Agent", status: "pending", detail: "Waiting" },
  { name: "Web Agent", status: "pending", detail: "Waiting" },
  { name: "Answer Agent", status: "pending", detail: "Waiting" },
];

export default function AgentsPage() {
  const { lastAgentRun } = useApp();
  const agents = lastAgentRun?.agents || DEFAULT_AGENTS;
  const timeline = lastAgentRun?.timeline || [];

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">Agent Workflow</h1>
          <p className="text-gray-400 text-sm">Any-Agent multi-agent pipeline visualization for judges.</p>
        </div>
        {!lastAgentRun && (
          <Link to="/chat" className="btn-primary text-sm">
            Run a query to see live agents
          </Link>
        )}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent, i) => (
          <AgentCard key={agent.name} agent={agent} index={i} />
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <AgentFlow agents={agents} />
        <div>
          <h3 className="text-sm font-medium text-gray-300 mb-4">Agent Timeline</h3>
          <AgentTimeline timeline={timeline} />
        </div>
      </div>
    </div>
  );
}
