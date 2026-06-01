import { useState } from "react";
import { Sparkles } from "lucide-react";
import { askContract } from "../services/api";

export default function AskPanel({ contractId }) {
  const [input, setInput]       = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading]   = useState(false);

  const send = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setMessages(prev => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const answer = await askContract(contractId, question);
      setMessages(prev => [...prev, { role: "ai", text: answer.answer }]);
    } catch {
      setMessages(prev => [...prev, { role: "ai", text: "Sorry, something went wrong." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-6">
      <h3 className="font-serif text-sm font-medium mb-3 text-gray-600 dark:text-gray-400">
        Ask about this contract
      </h3>

      {/* Message history */}
      {messages.length > 0 && (
        <div className="space-y-2 mb-3 max-h-48 overflow-y-auto">
          {messages.map((m, i) => (
            <div key={i} className={`text-sm px-3 py-2 rounded-xl max-w-[85%] ${
              m.role === "user"
                ? "bg-navy text-white ml-auto"
                : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            }`}>
              {m.text}
            </div>
          ))}
          {loading && (
            <div className="flex gap-1 px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-xl w-16">
              {[0,1,2].map(i => (
                <span key={i} className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Input row */}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
          placeholder='e.g. "Can I exit before the renewal date?"'
          className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-gray-400 transition-colors"
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="bg-navy text-gold px-4 py-2.5 rounded-xl text-sm flex items-center gap-2 disabled:opacity-40 transition-opacity"
        >
          <Sparkles size={14} /> Ask
        </button>
      </div>
    </div>
  );
}
