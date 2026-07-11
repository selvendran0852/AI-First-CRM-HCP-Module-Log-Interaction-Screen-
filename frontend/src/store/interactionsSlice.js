import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { createInteraction, updateInteraction } from "../api/client";

const initialForm = {
  hcp_id: null,
  hcp_name: "",
  interaction_type: "Meeting",
  occurred_at: new Date().toISOString().slice(0, 16),
  attendees: "",
  topics_discussed: "",
  materials_shared: "",
  samples_distributed: "",
  sentiment: "neutral",
  outcomes: "",
  follow_up_actions: "",
};

export const submitInteraction = createAsyncThunk(
  "interactions/submit",
  async (_, { getState }) => {
    const { form } = getState().interactions;
    return createInteraction({
      ...form,
      occurred_at: new Date(form.occurred_at).toISOString(),
      source_channel: "form",
    });
  }
);

export const editCurrentInteraction = createAsyncThunk(
  "interactions/edit",
  async ({ id, updates }) => updateInteraction(id, updates)
);

const interactionsSlice = createSlice({
  name: "interactions",
  initialState: {
    form: initialForm,
    currentInteractionId: null,
    suggestedFollowUps: [],
    status: "idle", // idle | saving | saved | error
    error: null,
  },
  reducers: {
    updateField(state, action) {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    setSuggestedFollowUps(state, action) {
      state.suggestedFollowUps = action.payload;
    },
    /** Lets the chat agent's structured result populate the form live. */
    hydrateFromAgentResult(state, action) {
      const r = action.payload;
      if (r.hcp_name) state.form.hcp_name = r.hcp_name;
      state.currentInteractionId = r.interaction_id || state.currentInteractionId;
    },
    resetForm(state) {
      state.form = initialForm;
      state.currentInteractionId = null;
      state.suggestedFollowUps = [];
      state.status = "idle";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitInteraction.pending, (state) => {
        state.status = "saving";
      })
      .addCase(submitInteraction.fulfilled, (state, action) => {
        state.status = "saved";
        state.currentInteractionId = action.payload.id;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.status = "error";
        state.error = action.error.message;
      })
      .addCase(editCurrentInteraction.fulfilled, (state) => {
        state.status = "saved";
      });
  },
});

export const { updateField, setSuggestedFollowUps, hydrateFromAgentResult, resetForm } =
  interactionsSlice.actions;
export default interactionsSlice.reducer;
