import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { updateField } from "../store/interactionsSlice";

export default function FollowUpSuggestions() {
  const dispatch = useDispatch();
  const { suggestedFollowUps, form } = useSelector((s) => s.interactions);

  if (!suggestedFollowUps.length) return null;

  const appendSuggestion = (text) => {
    const next = form.follow_up_actions ? `${form.follow_up_actions}\n${text}` : text;
    dispatch(updateField({ field: "follow_up_actions", value: next }));
  };

  return (
    <div>
      <label style={{ fontSize: 12, fontWeight: 500, color: "var(--color-muted)" }}>
        AI Suggested Follow-ups
      </label>
      <ul className="suggestion-list">
        {suggestedFollowUps.map((s, i) => (
          <li key={i} onClick={() => appendSuggestion(s)} title="Click to add to Follow-up Actions">
            + {s}
          </li>
        ))}
      </ul>
    </div>
  );
}
