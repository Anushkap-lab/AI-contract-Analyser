import { useState } from "react";
import { Sparkles } from "lucide-react";
import { askQuestion } from "../services/api";

export default function AskPanel({ contractId }) {
  const [input, setInput]     = useState("");
  const [answer, setAnswer]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const send = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setAnswer("");
    setError("");
    setLoading(true);
    try {
      const res = await askQuestion(question, contractId);
      setAnswer(res);
    } catch {
      setError("Sorry, something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };
    async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setMessages(prev => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const answer = await askQuestion(question, contractId);
      setMessages(prev => [...prev, { role: "ai", text: answer }]);
    } catch {
      setMessages(prev => [...prev, { role: "ai", text: "Sorry, something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ask-panel">

      <h3 className="sec-title">
        Ask about this contract
      </h3>

      {/* Input row */}
      <div className="ask-bar">
        <input
          className="ask-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
          placeholder='e.g. "Can I exit before the renewal date?"'
          disabled={loading}
        />
        <button
          className="ask-btn"
          onClick={send}
          disabled={!input.trim() || loading}
        >
          {loading
            ? <><span className="ask-spinner" /> Thinking...</>
            : <><Sparkles size={14} /> Ask AI</>}
        </button>
      </div>

      {/* Latest answer only — no history */}
      {answer && (
        <div className="summary-box" style={{ marginTop: "0.75rem" }}>
          <div className="summary-label">Answer</div>
          <div className="summary-text">{answer}</div>
        </div>
      )}

      {error && (
        <div className="error-box" style={{ marginTop: "0.75rem" }}>{error}</div>
      )}

    </div>
  );
}