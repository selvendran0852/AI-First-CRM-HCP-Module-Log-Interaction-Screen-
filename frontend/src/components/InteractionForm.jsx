import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { resetForm, submitInteraction, updateField } from "../store/interactionsSlice";
import FollowUpSuggestions from "./FollowUpSuggestions";

const SENTIMENTS = [
  { value: "positive", label: "Positive" },
  { value: "neutral", label: "Neutral" },
  { value: "negative", label: "Negative" },
];

export default function InteractionForm() {
  const dispatch = useDispatch();
  const { form, status } = useSelector((s) => s.interactions);

  const set = (field) => (e) => dispatch(updateField({ field, value: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    dispatch(submitInteraction());
  };

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h2>Interaction Details</h2>

      <div className="field-row">
        <div className="field">
          <label>HCP Name</label>
          <input
            placeholder="Search or select HCP..."
            value={form.hcp_name}
            onChange={set("hcp_name")}
            required
          />
        </div>
        <div className="field">
          <label>Interaction Type</label>
          <select value={form.interaction_type} onChange={set("interaction_type")}>
            <option>Meeting</option>
            <option>Call</option>
            <option>Email</option>
            <option>Conference</option>
            <option>Virtual</option>
          </select>
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Date &amp; Time</label>
          <input type="datetime-local" value={form.occurred_at} onChange={set("occurred_at")} />
        </div>
        <div className="field">
          <label>Attendees</label>
          <input placeholder="Enter names or search..." value={form.attendees} onChange={set("attendees")} />
        </div>
      </div>

      <div className="field">
        <label>Topics Discussed</label>
        <textarea
          placeholder="Enter key discussion points..."
          value={form.topics_discussed}
          onChange={set("topics_discussed")}
        />
      </div>

      <div className="field-row" style={{ marginTop: 14 }}>
        <div className="field">
          <label>Materials Shared</label>
          <input
            placeholder="No materials added"
            value={form.materials_shared}
            onChange={set("materials_shared")}
          />
        </div>
        <div className="field">
          <label>Samples Distributed</label>
          <input
            placeholder="No samples added"
            value={form.samples_distributed}
            onChange={set("samples_distributed")}
          />
        </div>
      </div>

      <div className="field">
        <label>Observed / Inferred HCP Sentiment</label>
        <div className="sentiment-row">
          {SENTIMENTS.map((s) => (
            <label key={s.value} className={`sentiment-option ${s.value}`}>
              <input
                type="radio"
                name="sentiment"
                value={s.value}
                checked={form.sentiment === s.value}
                onChange={set("sentiment")}
              />
              {s.label}
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <label>Outcomes</label>
        <textarea
          placeholder="Key outcomes or agreements..."
          value={form.outcomes}
          onChange={set("outcomes")}
        />
      </div>

      <div className="field">
        <label>Follow-up Actions</label>
        <textarea
          placeholder="Enter next steps or tasks..."
          value={form.follow_up_actions}
          onChange={set("follow_up_actions")}
        />
      </div>

      <FollowUpSuggestions />

      <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
        <button type="submit" className="btn btn-primary" disabled={status === "saving"}>
          {status === "saving" ? "Logging..." : "Log Interaction"}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => dispatch(resetForm())}>
          Clear
        </button>
      </div>
    </form>
  );
}
