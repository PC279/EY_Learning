import { useEffect, useRef, useState } from "react";
import { BookOpen, Send } from "lucide-react";
import { answerApproval, sendMessage } from "./api.js";
import Message, { ThinkingRow } from "./components/Message.jsx";

// The five test scenarios from the exercise, shown as one-click suggestions.
const SUGGESTIONS = [
  "Find books related to Python programming.",
  "Is Python Crash Course available?",
  "Reserve Python Crash Course for Ahmed.",
  "Show me books related to artificial intelligence.",
  "Reserve Deep Learning for Priya.",
];

// A random ID per browser tab, so the server keeps a separate conversation for each tab.
const newSessionId = () => crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;

export default function App() {
  const [sessionId] = useState(newSessionId);
  // Each message: { id, role: "user" | "assistant" | "error", text, toolsUsed, approval, approvalStatus }
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  // A reservation is waiting while an assistant message has approval details but no answer yet.
  const waitingForApproval = messages.some((m) => m.approval && !m.approvalStatus);

  // Keep the newest message in view.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const addMessage = (msg) => setMessages((prev) => [...prev, { id: crypto.randomUUID?.() ?? Math.random(), ...msg }]);

  // Turn the server's JSON into an assistant message.
  const addAssistantReply = (data) =>
    addMessage({ role: "assistant", text: data.reply, toolsUsed: data.tools_used, approval: data.approval });

  // Shared wrapper: show "thinking", call the server, show the reply or the error.
  async function callServer(request) {
    setLoading(true);
    try {
      addAssistantReply(await request());
    } catch (err) {
      addMessage({ role: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  function send(text) {
    const message = text.trim();
    if (!message || loading || waitingForApproval) return;
    addMessage({ role: "user", text: message });
    setInput("");
    callServer(() => sendMessage(sessionId, message));
  }

  function handleApproval(messageId, approved) {
    // Mark the buttons as answered right away, then let the server do the real work.
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, approvalStatus: approved ? "confirmed" : "cancelled" } : m))
    );
    callServer(() => answerApproval(sessionId, approved));
  }

  return (
    <main className="app">
      <section className="chat" aria-label="AI Library Assistant">
        <header className="chat-header">
          <BookOpen size={22} aria-hidden="true" />
          <div>
            <h1>AI Library Assistant</h1>
            <p>Book Search &amp; Reservations</p>
          </div>
        </header>

        <div className="messages" aria-live="polite">
          {messages.length === 0 && (
            <div className="welcome">
              <p>Hi! I can search the library catalogue and reserve books. Try one of these:</p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} type="button" className="pill" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <Message key={m.id} message={m} disabled={loading} onApproval={handleApproval} />
          ))}
          {loading && <ThinkingRow />}
          <div ref={bottomRef} />
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault(); // stop the browser from reloading the page
            send(input);
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={waitingForApproval ? "Confirm or cancel the reservation first" : "Type your message..."}
            disabled={loading || waitingForApproval}
            aria-label="Message"
          />
          <button type="submit" className="send" disabled={!input.trim() || loading || waitingForApproval} aria-label="Send message">
            <Send size={18} aria-hidden="true" />
          </button>
        </form>
      </section>
    </main>
  );
}
