import { useState, useRef, useEffect } from "react";
import { sendChat, setPreferences } from "../api";

function ChatInterface({ resumeId, onPreferencesSet }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "سلام! من دستیار هوشمند جستجوی کار هستم.\n\n" +
        "لطفا ابتدا رزومه خود را آپلود کنید، سپس ترجیحات شغلی خود را اینجا بنویسید.\n\n" +
        "مثال:\n" +
        '- "دنبال کار ریموت بک‌اند با پایتون، حقوق بالای ۲۰۰۰ دلار"\n' +
        '- "Looking for a frontend React developer role in Tehran"\n' +
        '- "فول‌استک، تهران یا ریموت، فریم‌ورک جنگو"',
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setSending(true);

    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    try {
      // If resume is uploaded, treat the message as preferences
      if (resumeId) {
        const data = await setPreferences(resumeId, text);
        onPreferencesSet(data.preferences.id);

        const parsed = data.parsed || {};
        let summary = "ترجیحات شغلی شما ذخیره شد:\n";

        if (parsed.job_type) summary += `\n- نوع کار: ${parsed.job_type}`;
        if (parsed.locations?.length > 0)
          summary += `\n- مکان: ${parsed.locations.join(", ")}`;
        if (parsed.fields?.length > 0)
          summary += `\n- حوزه: ${parsed.fields.join(", ")}`;
        if (parsed.min_salary)
          summary += `\n- حداقل حقوق: $${parsed.min_salary}`;
        if (parsed.keywords?.length > 0)
          summary += `\n- کلمات کلیدی: ${parsed.keywords.join(", ")}`;

        summary +=
          "\n\nحالا می‌توانید دکمه «شروع جستجوی مشاغل» را بزنید.";

        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: summary },
        ]);
      } else {
        // Regular chat
        const data = await sendChat(text);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.content },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `خطا: ${err.message}. لطفا دوباره تلاش کنید.`,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 flex flex-col h-[600px]">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <h2 className="font-bold text-gray-900">گفتگو</h2>
        <p className="text-sm text-gray-500">
          {resumeId
            ? "ترجیحات شغلی خود را بنویسید"
            : "ابتدا رزومه خود را آپلود کنید"}
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.role === "user" ? "justify-start" : "justify-end"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-brand-600 text-white rounded-br-sm"
                  : "bg-gray-100 text-gray-800 rounded-bl-sm"
              }`}
            >
              <p className="text-sm whitespace-pre-line leading-relaxed">
                {msg.content}
              </p>
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-end">
            <div className="bg-gray-100 rounded-xl px-4 py-3 rounded-bl-sm">
              <span className="flex gap-1">
                <span className="pulse-dot w-2 h-2 bg-gray-400 rounded-full" />
                <span className="pulse-dot w-2 h-2 bg-gray-400 rounded-full" />
                <span className="pulse-dot w-2 h-2 bg-gray-400 rounded-full" />
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-100">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              resumeId
                ? "ترجیحات شغلی خود را بنویسید..."
                : "پیام خود را بنویسید..."
            }
            rows={1}
            className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="bg-brand-600 hover:bg-brand-700 disabled:bg-gray-300 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <svg
              className="w-5 h-5 rotate-180"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;
