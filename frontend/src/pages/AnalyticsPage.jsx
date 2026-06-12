import { AnalyticsDashboard } from "../components/analytics/AnalyticsCharts";

export default function AnalyticsPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Analytics</h1>
        <p className="text-gray-400 text-sm">Privacy and confidence metrics across your queries.</p>
      </div>
      <AnalyticsDashboard />
    </div>
  );
}
