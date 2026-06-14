import { useState } from "react";
import { Sparkles } from "lucide-react";
import { askQuestion } from "../services/api"

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
      const answer = await askQuestion(contractId, question);
      setMessages(prev => [...prev, { role: "ai", text: answer.answer }]);
    } catch {
      setMessages(prev => [...prev, { role: "ai", text: "Sorry, something went wrong." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ask-panel">
      <h3 className="ask-title">
        Ask about this contract
      </h3>

      {messages.length > 0 && (
        <div className="message-list">
          {messages.map((m, i) => (
            <div key={i} className={`message ${m.role === "user" ? "user" : "ai"}`}>
              {m.text}
            </div>
          ))}
          {loading && (
            <div className="message ai typing">
              {[0,1,2].map(i => (
                <span key={i}
                  style={{ animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          )}
        </div>
      )}

      <div className="ask-row">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
          placeholder='e.g. "Can I exit before the renewal date?"'
          className="ask-input"
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="ask-button"
        >
          <Sparkles size={14} /> Ask
        </button>
      </div>
    </div>
  );
}
