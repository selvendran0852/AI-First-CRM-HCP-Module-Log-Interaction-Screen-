from typing import Optional, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state threaded through every node of the LangGraph agent."""

    session_id: str
    user_message: str          # raw text typed into the chat panel
    intent: str                # classified intent, drives routing
    intent_args: dict          # structured args extracted for the chosen tool
    tool_calls: list[str]      # names of tools invoked this turn (for the demo video / UI)
    tool_result: dict          # structured result payload from the tool that ran
    interaction_id: Optional[str]  # target interaction for edit/history tools
    reply: str                 # final natural-language reply shown to the rep
