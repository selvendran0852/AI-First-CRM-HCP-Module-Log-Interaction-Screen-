"""
The LangGraph agent's toolset for sales-related HCP activities.

Each tool is a plain Python function of (db_session, state) -> dict.
They are wired into LangGraph nodes in graph.py. Keeping the tool logic
here (framework-agnostic) makes them independently unit-testable and
reusable from the REST API (see routers/interactions.py) as well as
from the chat agent.

Tools implemented (5, as required):
    1. log_interaction      (mandatory)
    2. edit_interaction     (mandatory)
    3. get_interaction_history
    4. suggest_followups
    5. search_materials
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.llm import chat_completion, extract_json

logger = logging.getLogger("hcp_crm.tools")

# A small in-memory catalog stands in for a real Materials/Samples master
# database (out of scope for this assignment's DB schema, but a real
# implementation would back this with its own table).
MATERIALS_CATALOG = [
    {"id": "m1", "name": "OncoBoost Phase III Efficacy Deck", "type": "material"},
    {"id": "m2", "name": "OncoBoost Safety Profile One-Pager", "type": "material"},
    {"id": "m3", "name": "CardioPlus Dosing Guide", "type": "material"},
    {"id": "s1", "name": "OncoBoost 10mg Sample Pack", "type": "sample"},
    {"id": "s2", "name": "CardioPlus Starter Sample", "type": "sample"},
]


# ---------------------------------------------------------------------------
# Tool 1 (mandatory): log_interaction
# ---------------------------------------------------------------------------
def log_interaction(db: Session, args: dict) -> dict:
    """
    Capture a new HCP interaction.

    Accepts either already-structured fields (from the Log Interaction form)
    or a single free-text `raw_text` string (from the chat panel), in which
    case the LLM performs entity extraction + summarization to populate the
    structured record: HCP name, interaction type, topics discussed,
    sentiment, materials/samples mentioned, outcomes, and follow-ups.
    """
    raw_text = args.get("raw_text")

    if raw_text:
        extracted = extract_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an entity-extraction assistant for a pharma CRM. "
                        "Given a field rep's free-text note about a meeting with a "
                        "healthcare professional (HCP), extract a JSON object with keys: "
                        "hcp_name (string), interaction_type (one of Meeting, Call, Email, "
                        "Conference, Virtual), topics_discussed (string), "
                        "materials_shared (comma-separated string or empty), "
                        "samples_distributed (comma-separated string or empty), "
                        "sentiment (one of positive, neutral, negative), "
                        "outcomes (string), follow_up_actions (string). "
                        "Return ONLY the JSON object."
                    ),
                },
                {"role": "user", "content": raw_text},
            ]
        )
        args = {**extracted, **{k: v for k, v in args.items() if v}}

    hcp_name = (args.get("hcp_name") or "Unknown HCP").strip()
    hcp = db.query(models.HCP).filter(models.HCP.name.ilike(hcp_name)).first()
    if not hcp:
        hcp = models.HCP(name=hcp_name)
        db.add(hcp)
        db.flush()

    interaction = models.Interaction(
        hcp_id=hcp.id,
        interaction_type=args.get("interaction_type", "Meeting"),
        occurred_at=args.get("occurred_at") or datetime.utcnow(),
        attendees=args.get("attendees"),
        topics_discussed=args.get("topics_discussed"),
        materials_shared=args.get("materials_shared"),
        samples_distributed=args.get("samples_distributed"),
        sentiment=args.get("sentiment", "neutral"),
        outcomes=args.get("outcomes"),
        follow_up_actions=args.get("follow_up_actions"),
        source_raw_text=raw_text,
        source_channel="chat" if raw_text else "form",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return {
        "tool": "log_interaction",
        "interaction_id": interaction.id,
        "hcp_name": hcp.name,
        "summary": f"Logged {interaction.interaction_type} with {hcp.name} "
        f"({interaction.sentiment} sentiment).",
    }


# ---------------------------------------------------------------------------
# Tool 2 (mandatory): edit_interaction
# ---------------------------------------------------------------------------
def edit_interaction(db: Session, args: dict) -> dict:
    """
    Modify an already-logged interaction.

    Resolves the target record either by explicit `interaction_id`, or by
    "most recent interaction for <hcp_name>" when the rep refers to it
    conversationally (e.g. "actually, add that Dr. Smith also asked for the
    dosing guide"). Only the fields present in `updates` are changed.
    """
    interaction = None
    if args.get("interaction_id"):
        interaction = (
            db.query(models.Interaction)
            .filter(models.Interaction.id == args["interaction_id"])
            .first()
        )
    elif args.get("hcp_name"):
        hcp = db.query(models.HCP).filter(models.HCP.name.ilike(args["hcp_name"])).first()
        if hcp:
            interaction = (
                db.query(models.Interaction)
                .filter(models.Interaction.hcp_id == hcp.id)
                .order_by(models.Interaction.created_at.desc())
                .first()
            )

    if interaction is None:
        return {"tool": "edit_interaction", "error": "No matching interaction found to edit."}

    updates = args.get("updates", {})
    # If the rep phrased the edit as free text, ask the LLM to turn it into
    # a partial-update JSON against the current record.
    if args.get("raw_text") and not updates:
        current = {
            "interaction_type": interaction.interaction_type,
            "topics_discussed": interaction.topics_discussed,
            "materials_shared": interaction.materials_shared,
            "samples_distributed": interaction.samples_distributed,
            "sentiment": interaction.sentiment,
            "outcomes": interaction.outcomes,
            "follow_up_actions": interaction.follow_up_actions,
        }
        updates = extract_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You update pharma CRM interaction records. Given the CURRENT record "
                        "as JSON and an EDIT INSTRUCTION in free text, return a JSON object "
                        "containing ONLY the fields that should change, with their new full "
                        "values (merge with existing text where appropriate, don't just "
                        "append). Valid keys: interaction_type, topics_discussed, "
                        "materials_shared, samples_distributed, sentiment, outcomes, "
                        "follow_up_actions."
                    ),
                },
                {
                    "role": "user",
                    "content": f"CURRENT: {current}\n\nEDIT INSTRUCTION: {args['raw_text']}",
                },
            ]
        )

    for field, value in updates.items():
        if hasattr(interaction, field) and value is not None:
            setattr(interaction, field, value)

    db.commit()
    db.refresh(interaction)

    return {
        "tool": "edit_interaction",
        "interaction_id": interaction.id,
        "updated_fields": list(updates.keys()),
        "summary": f"Updated interaction {interaction.id[:8]} ({', '.join(updates.keys()) or 'no changes'}).",
    }


# ---------------------------------------------------------------------------
# Tool 3: get_interaction_history
# ---------------------------------------------------------------------------
def get_interaction_history(db: Session, args: dict) -> dict:
    """
    Retrieve prior interactions for a given HCP, so the rep (or the LLM,
    for context when drafting follow-ups) can see interaction history
    before the next meeting.
    """
    hcp_name = args.get("hcp_name", "")
    hcp = db.query(models.HCP).filter(models.HCP.name.ilike(f"%{hcp_name}%")).first()
    if not hcp:
        return {"tool": "get_interaction_history", "error": f"No HCP found matching '{hcp_name}'."}

    limit = int(args.get("limit", 5))
    rows = (
        db.query(models.Interaction)
        .filter(models.Interaction.hcp_id == hcp.id)
        .order_by(models.Interaction.occurred_at.desc())
        .limit(limit)
        .all()
    )
    history = [
        {
            "id": r.id,
            "type": r.interaction_type,
            "date": r.occurred_at.isoformat() if r.occurred_at else None,
            "topics": r.topics_discussed,
            "sentiment": r.sentiment,
            "outcomes": r.outcomes,
        }
        for r in rows
    ]
    if history:
        lines = "\n".join(f"- {h['date']}: {h['topics']} ({h['sentiment']})" for h in history)
        summary = f"Last {len(history)} interaction(s) with {hcp.name}:\n{lines}"
    else:
        summary = f"No prior interactions found for {hcp.name}."

    return {
        "tool": "get_interaction_history",
        "hcp_name": hcp.name,
        "history": history,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Tool 4: suggest_followups
# ---------------------------------------------------------------------------
def suggest_followups(db: Session, args: dict) -> dict:
    """
    Generate AI-suggested next-best-actions for an interaction (mirrors the
    "AI Suggested Follow-ups" panel in the Log Interaction screen), using
    the interaction content plus recent history for that HCP as context.
    """
    interaction = None
    if args.get("interaction_id"):
        interaction = (
            db.query(models.Interaction)
            .filter(models.Interaction.id == args["interaction_id"])
            .first()
        )
    elif args.get("hcp_name"):
        hcp = db.query(models.HCP).filter(models.HCP.name.ilike(f"%{args['hcp_name']}%")).first()
        if hcp:
            interaction = (
                db.query(models.Interaction)
                .filter(models.Interaction.hcp_id == hcp.id)
                .order_by(models.Interaction.occurred_at.desc())
                .first()
            )
    if interaction is None:
        return {"tool": "suggest_followups", "error": "No interaction found to base suggestions on."}

    hcp = db.query(models.HCP).filter(models.HCP.id == interaction.hcp_id).first()
    history = (
        db.query(models.Interaction)
        .filter(models.Interaction.hcp_id == interaction.hcp_id)
        .order_by(models.Interaction.occurred_at.desc())
        .limit(3)
        .all()
    )
    history_text = "\n".join(
        f"- {h.occurred_at}: {h.topics_discussed} (sentiment: {h.sentiment})" for h in history
    )

    raw = chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You are a pharma sales-enablement assistant. Given the latest interaction "
                    "and recent history with an HCP, suggest 3 short, concrete follow-up actions "
                    "a field rep should take next (e.g. schedule a follow-up, send a specific "
                    "material, add to an advisory board list). One action per line, no numbering, "
                    "no extra commentary."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"HCP: {hcp.name if hcp else 'Unknown'}\n"
                    f"Latest topics: {interaction.topics_discussed}\n"
                    f"Latest sentiment: {interaction.sentiment}\n"
                    f"Latest outcomes: {interaction.outcomes}\n"
                    f"Recent history:\n{history_text or 'none'}"
                ),
            },
        ]
    )
    suggestions = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]

    top = suggestions[:3]
    return {
        "tool": "suggest_followups",
        "interaction_id": interaction.id,
        "suggestions": top,
        "summary": "Here are 3 suggested follow-ups:\n" + "\n".join(f"- {s}" for s in top),
    }


# ---------------------------------------------------------------------------
# Tool 5: search_materials
# ---------------------------------------------------------------------------
def search_materials(db: Session, args: dict) -> dict:
    """
    Search the marketing materials / sample catalog (the "Materials Shared"
    and "Samples Distributed" pickers in the UI) so the rep or the chat
    agent can attach the right item to the interaction being logged.
    """
    query = (args.get("query") or "").lower().strip()
    item_type = args.get("type")  # "material" | "sample" | None

    results = [
        item
        for item in MATERIALS_CATALOG
        if (not query or query in item["name"].lower())
        and (not item_type or item["type"] == item_type)
    ]
    names = ", ".join(r["name"] for r in results) or "no matches"
    return {
        "tool": "search_materials",
        "query": query,
        "results": results,
        "summary": f"Found: {names}",
    }


TOOL_REGISTRY = {
    "log_interaction": log_interaction,
    "edit_interaction": edit_interaction,
    "get_interaction_history": get_interaction_history,
    "suggest_followups": suggest_followups,
    "search_materials": search_materials,
}
