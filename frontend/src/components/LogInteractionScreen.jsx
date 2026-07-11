import React from "react";
import ChatPanel from "./ChatPanel";
import InteractionForm from "./InteractionForm";

export default function LogInteractionScreen() {
  return (
    <div className="log-screen">
      <InteractionForm />
      <ChatPanel />
    </div>
  );
}
