import { useState, useEffect } from "react";
import { getLLMStatus, switchLLMProvider } from "../api";

const PROVIDERS = [
  { value: "claude", label: "Claude (Browser)" },
  { value: "openai", label: "ChatGPT / OpenAI" },
];

function LLMSelector() {
  const [status, setStatus] = useState(null);
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    getLLMStatus()
      .then(setStatus)
      .catch(() => {});
  }, []);

  const handleSwitch = async (provider) => {
    if (switching) return;
    setSwitching(true);
    try {
      const data = await switchLLMProvider(provider);
      setStatus({ provider: data.provider, available: data.available });
    } catch {
      // Ignore
    } finally {
      setSwitching(false);
    }
  };

  if (!status) return null;

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-gray-500">LLM:</label>
      <select
        value={status.provider}
        onChange={(e) => handleSwitch(e.target.value)}
        disabled={switching}
        className="text-xs border border-gray-300 rounded px-1.5 py-1 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white disabled:opacity-50"
      >
        {PROVIDERS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>
      <span
        className={`w-2 h-2 rounded-full ${
          status.available ? "bg-green-500" : "bg-red-400"
        }`}
        title={status.available ? "Ready" : "Not available"}
      />
      {switching && (
        <span className="w-3 h-3 border-2 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
      )}
    </div>
  );
}

export default LLMSelector;
