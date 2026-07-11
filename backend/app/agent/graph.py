"""
The LangGraph agent that powers the "AI Assistant" chat panel on the
Log Interaction Screen.

Flow:
    classify_intent  --routes to-->  one of the 5 tool nodes  --> respond
                       (falls through to `chat` node for general Q&A)

The agent is rebuilt per-request (see get_agent) so it can close over the
current DB session — this keeps SQLAlchemy session lifetime scoped to a
single FastAPI request, which is the safe pattern for a web app.
"""

from __future__ import annotations

import json
import logging

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agent.state import AgentState
from app.agent.tools import TOOL_REGISTRY
from app.llm import chat_completion, extract_json

logger = logging.getLogger("hcp_crm.agent")

INTENT_TOOL_MAP = {
    "log_interaction": "log_interaction",
    "edit_interaction": "edit_interaction",
    "get_history": "get_interaction_history",
    "suggest_followups": "suggest_followups",
    "search_materials": "search_materials",
}


def build_agent(db: Session):
    """Compile a LangGraph StateGraph bound to the given DB session."""

    def classify_intent(state: AgentState) -> AgentState:
        """LLM node: decide which of the 5 tools (or plain chat) to invoke,
        and pull out the arguments that tool needs."""
        result = extract_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are the router for a pharma CRM AI agent. Classify the field "
                        "rep's chat message into exactly one intent and extract arguments. "
                        "Return JSON: {\"intent\": one of "
                        "['log_interaction','edit_interaction','get_history',"
                        "'suggest_followups','search_materials','chat'], \"args\": {...}}. "
                        "For log_interaction: args = {\"raw_text\": <the message>}. "
                        "For edit_interaction: args = {\"raw_text\": <the message>, "
                        "\"hcp_name\": <if mentioned>}. "
                        "For get_history: args = {\"hcp_name\": <name>}. "
                        "For suggest_followups: args = {\"interaction_id\": <if known, else null>, "
                        "\"hcp_name\": <HCP name if mentioned, else null>}. "
                        "For search_materials: args = {\"query\": <search text>}. "
                        "For chat: args = {}. "
                        "Use 'chat' only if none of the other intents clearly apply."
                    ),
                },
                {"role": "user", "content": state["user_message"]},
            ]
        )
        state["intent"] = result.get("intent", "chat")
        state["intent_args"] = result.get("args", {}) or {}
        return state

    def make_tool_node(tool_key: str):
        tool_fn = TOOL_REGISTRY[tool_key]

        def node(state: AgentState) -> AgentState:
            args = dict(state.get("intent_args", {}))
            if state.get("interaction_id") and not args.get("interaction_id"):
                args["interaction_id"] = state["interaction_id"]
            try:
                result = tool_fn(db, args)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tool %s failed", tool_key)
                result = {"tool": tool_key, "error": str(exc)}
            state["tool_result"] = result
            state["tool_calls"] = state.get("tool_calls", []) + [tool_key]
            if result.get("interaction_id"):
                state["interaction_id"] = result["interaction_id"]
            return state

        return node

    def chat_node(state: AgentState) -> AgentState:
        reply = chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant embedded in a pharma CRM's "
                        "Log Interaction screen. Answer the field rep's question concisely. "
                        "If they seem to want to log or edit an interaction, tell them they "
                        "can just describe it in plain language and you'll handle it."
                    ),
                },
                {"role": "user", "content": state["user_message"]},
            ]
        )
        state["tool_result"] = {"tool": "chat"}
        state["tool_calls"] = state.get("tool_calls", [])
        state["reply"] = reply
        return state

    def respond(state: AgentState) -> AgentState:
        if state.get("reply"):
            return state  # chat_node already produced a natural reply
        result = state.get("tool_result", {})
        if result.get("error"):
            state["reply"] = f"I couldn't do that: {result['error']}"
        else:
            state["reply"] = result.get("summary") or json.dumps(result)
        return state

    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("chat", chat_node)
    for intent_name, tool_key in INTENT_TOOL_MAP.items():
        graph.add_node(intent_name, make_tool_node(tool_key))
    graph.add_node("respond", respond)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        lambda state: state["intent"],
        {**{k: k for k in INTENT_TOOL_MAP}, "chat": "chat"},
    )
    for intent_name in INTENT_TOOL_MAP:
        graph.add_edge(intent_name, "respond")
    graph.add_edge("chat", "respond")
    graph.add_edge("respond", END)

    return graph.compile()


def run_agent(db: Session, session_id: str, user_message: str, interaction_id: str | None = None) -> AgentState:
    agent = build_agent(db)
    initial_state: AgentState = {
        "session_id": session_id,
        "user_message": user_message,
        "interaction_id": interaction_id,
        "tool_calls": [],
    }
    return agent.invoke(initial_state)
