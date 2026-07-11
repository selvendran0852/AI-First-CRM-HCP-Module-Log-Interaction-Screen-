import React from "react";
import LogInteractionScreen from "./components/LogInteractionScreen";

export default function App() {
  return (
    <div className="app-shell">
      <div className="screen-title">Log HCP Interaction</div>
      <LogInteractionScreen />
    </div>
  );
}
