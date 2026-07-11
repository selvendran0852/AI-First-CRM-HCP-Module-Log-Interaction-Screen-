from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class HCPBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    institution: Optional[str] = None


class HCPCreate(HCPBase):
    pass


class HCPOut(HCPBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


class InteractionBase(BaseModel):
    hcp_id: str
    interaction_type: str = "Meeting"
    occurred_at: datetime
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None
    sentiment: str = "neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionCreate(InteractionBase):
    source_raw_text: Optional[str] = None
    source_channel: str = "form"


class InteractionUpdate(BaseModel):
    """All fields optional — this backs the `edit_interaction` tool and PATCH endpoint."""

    interaction_type: Optional[str] = None
    occurred_at: Optional[datetime] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionOut(InteractionBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_channel: str
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_calls: list[str] = []
    tool_result: Optional[dict] = None
    interaction: Optional[InteractionOut] = None
