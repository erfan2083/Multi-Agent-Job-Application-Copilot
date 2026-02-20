import { useRef, useEffect } from "react";

function StatusStream({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-3 border-b border-gray-100">
        <h3 className="font-bold text-gray-900 text-sm">وضعیت جستجو</h3>
      </div>

      <div className="max-h-48 overflow-y-auto p-3 space-y-2">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-2 text-xs ${
              msg.type === "error" ? "text-red-600" : "text-gray-600"
            }`}
          >
            <span className="shrink-0 mt-0.5">
              {msg.type === "error" ? (
                <svg
                  className="w-3.5 h-3.5 text-red-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              ) : (
                <svg
                  className="w-3.5 h-3.5 text-brand-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              )}
            </span>
            <span className="leading-relaxed">{msg.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

export default StatusStream;
