import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Pie,
  PieChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useApp } from "../../context/AppContext";

const COLORS = ["#D4622A", "#EF4444", "#3B82F6"];

function MetricCard({ label, value, sub }) {
  return (
    <div className="card p-5">
      <div className="text-xs uppercase tracking-wider text-gray-500 mb-2">{label}</div>
      <div className="text-3xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

export default function PrivacyChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
        <XAxis dataKey="label" stroke="#6B7280" fontSize={11} />
        <YAxis domain={[0, 100]} stroke="#6B7280" fontSize={11} />
        <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1F2937" }} />
        <Line type="monotone" dataKey="privacy" stroke="#D4622A" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ConfidenceChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
        <XAxis dataKey="range" stroke="#6B7280" fontSize={11} />
        <YAxis stroke="#6B7280" fontSize={11} />
        <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1F2937" }} />
        <Bar dataKey="count" fill="#D4622A" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LocalVsWebChart({ local, web }) {
  const data = [
    { name: "Local", value: local },
    { name: "Web", value: web },
  ];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1F2937" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function AnalyticsDashboard() {
  const { analytics, analyticsSummary } = useApp();

  const trendData = analytics.slice(-10).map((a, i) => ({
    label: `#${i + 1}`,
    privacy: a.privacy,
    confidence: a.confidence,
  }));

  const buckets = [
    { range: "0-40", count: analytics.filter((a) => a.confidence <= 40).length },
    { range: "41-70", count: analytics.filter((a) => a.confidence > 40 && a.confidence <= 70).length },
    { range: "71-100", count: analytics.filter((a) => a.confidence > 70).length },
  ];

  const localCount = analytics.filter((a) => !a.webUsed).length;
  const webCount = analytics.filter((a) => a.webUsed).length;

  return (
    <div className="space-y-8">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Average Privacy Score" value={analyticsSummary.avgPrivacy || "—"} />
        <MetricCard label="Average Confidence" value={analyticsSummary.avgConfidence || "—"} />
        <MetricCard label="Internet Requests Saved" value={analyticsSummary.saved} />
        <MetricCard label="Total Queries" value={analyticsSummary.total} />
      </div>
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="card p-4">
          <h3 className="text-sm font-medium mb-4 text-gray-300">Privacy Score Trend</h3>
          {trendData.length ? <PrivacyChart data={trendData} /> : <p className="text-gray-500 text-sm py-16 text-center">No data yet</p>}
        </div>
        <div className="card p-4">
          <h3 className="text-sm font-medium mb-4 text-gray-300">Confidence Distribution</h3>
          {analytics.length ? <ConfidenceChart data={buckets} /> : <p className="text-gray-500 text-sm py-16 text-center">No data yet</p>}
        </div>
        <div className="card p-4">
          <h3 className="text-sm font-medium mb-4 text-gray-300">Local vs Internet</h3>
          {analytics.length ? <LocalVsWebChart local={localCount} web={webCount} /> : <p className="text-gray-500 text-sm py-16 text-center">No data yet</p>}
        </div>
      </div>
    </div>
  );
}
