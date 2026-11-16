import ReactMarkdown from "react-markdown";
import { Bot } from "lucide-react";

// Renders one chat message. User messages are blue bubbles on the right;
// assistant and error messages sit on the left next to the bot icon.
export default function Message({ message, disabled, onApproval }) {
  const { id, role, text, toolsUsed, approval, approvalStatus } = message;

  if (role === "user") {
    return <div className="msg user"><div className="bubble">{text}</div></div>;
  }

  return (
    <div className={`msg assistant ${role === "error" ? "error" : ""}`}>
      <Bot size={18} className="bot-icon" aria-hidden="true" />
      <div className="body">
        {/* Models often reply in Markdown (lists, bold), so render it instead of showing ** symbols. */}
        <div className="text"><ReactMarkdown>{text}</ReactMarkdown></div>

        {/* Confirm/Cancel only appear when the server paused a reservation for approval. */}
        {approval && !approvalStatus && (
          <div className="actions">
            <button type="button" className="pill" disabled={disabled} onClick={() => onApproval(id, true)}>
              Confirm
            </button>
            <button type="button" className="pill" disabled={disabled} onClick={() => onApproval(id, false)}>
              Cancel
            </button>
          </div>
        )}
        {approvalStatus && (
          <p className={`status ${approvalStatus}`}>
            {approvalStatus === "confirmed" ? "Confirmed" : "Cancelled"}
          </p>
        )}

        {toolsUsed?.length > 0 && <p className="caption">Tool used: {toolsUsed.join(", ")}</p>}
      </div>
    </div>
  );
}

// Shown while waiting for the server.
export function ThinkingRow() {
  return (
    <div className="msg assistant">
      <Bot size={18} className="bot-icon" aria-hidden="true" />
      <div className="body"><p className="caption thinking">Thinking…</p></div>
    </div>
  );
}
