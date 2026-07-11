import { configureStore } from "@reduxjs/toolkit";
import chatReducer from "./chatSlice";
import interactionsReducer from "./interactionsSlice";

export const store = configureStore({
  reducer: {
    interactions: interactionsReducer,
    chat: chatReducer,
  },
});
