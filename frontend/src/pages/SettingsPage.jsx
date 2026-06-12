import { useApp } from "../context/AppContext";

export default function SettingsPage() {
  const { settings, setSettings, health } = useApp();
  const modelId = health?.model_id || "Qwen 3.5";

  const update = (key, value) => setSettings((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Settings</h1>
        <p className="text-gray-400 text-sm">Configure model and retrieval preferences.</p>
      </div>

      <div className="card p-6 space-y-6">
        <section>
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Model Settings</h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-500">Current Model</label>
              <div className="mt-1 px-3 py-2 rounded-lg bg-surface-elevated border border-border text-sm">
                {modelId}
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500">Temperature — {settings.temperature}</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settings.temperature}
                onChange={(e) => update("temperature", parseFloat(e.target.value))}
                className="w-full mt-2 accent-accent"
              />
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Retrieval</h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-500">Top K Retrieval — {settings.topK}</label>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={settings.topK}
                onChange={(e) => update("topK", parseInt(e.target.value, 10))}
                className="w-full mt-2 accent-accent"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">Chunk Size — {settings.chunkSize}</label>
              <input
                type="range"
                min="128"
                max="1024"
                step="128"
                value={settings.chunkSize}
                onChange={(e) => update("chunkSize", parseInt(e.target.value, 10))}
                className="w-full mt-2 accent-accent"
              />
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Privacy</h2>
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-gray-300">Internet Fallback</span>
            <input
              type="checkbox"
              checked={settings.internetFallback}
              onChange={(e) => update("internetFallback", e.target.checked)}
              className="w-4 h-4 accent-accent"
            />
          </label>
          <p className="text-xs text-gray-500 mt-2">
            When enabled, web search is used if local confidence is low.
          </p>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Appearance</h2>
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-gray-300">Dark Mode</span>
            <input
              type="checkbox"
              checked={settings.theme === "dark"}
              onChange={(e) => update("theme", e.target.checked ? "dark" : "light")}
              className="w-4 h-4 accent-accent"
            />
          </label>
        </section>
      </div>
    </div>
  );
}
