import React, { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { hydrateFromAgentResult, setSuggestedFollowUps, updateField } from "../store/interactionsSlice";
import { sendMessage } from "../store/chatSlice";

export default function ChatPanel() {
  const dispatch = useDispatch();
  const { messages, isTyping } = useSelector((s) => s.chat);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!draft.trim()) return;
    const text = draft;
    setDraft("");
    const action = await dispatch(sendMessage(text));
    const payload = action.payload;
    if (!payload) return;

    // Reflect agent side-effects back into the structured form so the two
    // input modes (form / chat) stay in sync, per the assignment spec.
    if (payload.tool_calls?.includes("suggest_followups") && payload.tool_result?.suggestions) {
      dispatch(setSuggestedFollowUps(payload.tool_result.suggestions));
    }
    if (payload.interaction) {

      const hcpName = payload.tool_result?.hcp_name || "";
      dispatch(hydrateFromAgentResult({ hcp_name: hcpName, interaction_id: payload.interaction.id }));
      dispatch(updateField({ field: "hcp_name", value: hcpName }));
      dispatch(updateField({ field: "topics_discussed", value: payload.interaction.topics_discussed || "" }));
      dispatch(updateField({ field: "sentiment", value: payload.interaction.sentiment || "neutral" }));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <div className="panel chat-panel">
      <div className="chat-header">AI Assistant</div>
      <div className="chat-subheader">Log interaction via chat</div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-bubble assistant">
            Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy,
            positive sentiment, shared brochure") or ask for help.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.role === "assistant" && m.toolCalls?.length > 0 && (
              <div className="chat-tool-tag">{m.toolCalls.join(", ")}</div>
            )}
            <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
          </div>
        ))}
        {isTyping && <div className="chat-bubble assistant">Thinking…</div>}
      </div>

      <div className="chat-input-row">
        <input
          placeholder="Describe interaction..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="btn btn-primary" onClick={handleSend}>
          Log
        </button>
      </div>
    </div>
  );
}
