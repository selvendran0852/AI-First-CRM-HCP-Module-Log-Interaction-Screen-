import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InteractionTypeEnum(str, enum.Enum):
    meeting = "Meeting"
    call = "Call"
    email = "Email"
    conference = "Conference"
    virtual = "Virtual"


class HCP(Base):
    """A Healthcare Professional the field rep engages with."""

    __tablename__ = "hcps"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False, index=True)
    specialty = Column(String(255), nullable=True)
    institution = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")


class Interaction(Base):
    """A single logged HCP interaction — the core entity of this task."""

    __tablename__ = "interactions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    hcp_id = Column(String(36), ForeignKey("hcps.id"), nullable=False)

    interaction_type = Column(Enum(InteractionTypeEnum), default=InteractionTypeEnum.meeting)
    occurred_at = Column(DateTime(timezone=True), nullable=False)

    attendees = Column(Text, nullable=True)  # comma-separated names
    topics_discussed = Column(Text, nullable=True)

    materials_shared = Column(Text, nullable=True)  # comma-separated
    samples_distributed = Column(Text, nullable=True)  # comma-separated

    sentiment = Column(Enum(SentimentEnum), default=SentimentEnum.neutral)
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)

    # Free-text the rep typed into chat, kept for auditability/traceability.
    source_raw_text = Column(Text, nullable=True)
    # "form" or "chat" — which UI path created/edited this record.
    source_channel = Column(String(20), default="form")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    hcp = relationship("HCP", back_populates="interactions")


class ChatMessage(Base):
    """Persisted conversational turns for the AI Assistant chat panel."""

    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    session_id = Column(String(36), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # "user" | "assistant" | "tool"
    content = Column(Text, nullable=False)
    tool_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
