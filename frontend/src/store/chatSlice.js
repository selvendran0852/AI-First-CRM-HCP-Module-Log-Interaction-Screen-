import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { sendChatMessage } from "../api/client";

const sessionId =
  window.localStorage.getItem("hcp_chat_session") ||
  (() => {
    const id = crypto.randomUUID();
    window.localStorage.setItem("hcp_chat_session", id);
    return id;
  })();

export const sendMessage = createAsyncThunk("chat/sendMessage", async (message) =>
  sendChatMessage(sessionId, message)
);

const chatSlice = createSlice({
  name: "chat",
  initialState: {
    sessionId,
    messages: [],
    isTyping: false,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.messages.push({ role: "user", content: action.meta.arg });
        state.isTyping = true;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isTyping = false;
        state.messages.push({
          role: "assistant",
          content: action.payload.reply,
          toolCalls: action.payload.tool_calls,
          toolResult: action.payload.tool_result,
          interaction: action.payload.interaction,
        });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isTyping = false;
        state.messages.push({
          role: "assistant",
          content: `Sorry, something went wrong: ${action.error.message}`,
        });
      });
  },
});

export default chatSlice.reducer;
