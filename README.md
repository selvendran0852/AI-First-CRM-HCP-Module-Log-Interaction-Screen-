# AI-First CRM — HCP Module: Log Interaction Screen

A reference implementation of the "Log Interaction Screen" for an AI-first CRM's
Healthcare Professional (HCP) module, built for field representatives. The screen
offers two equivalent ways to record an interaction — a **structured form** and a
**conversational AI Assistant** — backed by a **LangGraph** agent running on **Groq**.

## Tech stack

| Layer      | Choice                                             |
|------------|-----------------------------------------------------|
| Frontend   | React 18 + Redux Toolkit                            |
| Backend    | Python + FastAPI                                    |
| AI agent   | LangGraph (StateGraph)                               |
| LLM        | Groq `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (fallback) |
| Database   | PostgreSQL or MySQL via SQLAlchemy                   |
| Font       | Google Inter                                         |

## Repository layout

```
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph.py       # LangGraph StateGraph: intent routing → tools → reply
│   │   │   ├── state.py       # AgentState TypedDict
│   │   │   └── tools.py       # the 5 sales-activity tools
│   │   ├── routers/
│   │   │   ├── chat.py        # POST /api/chat — conversational path
│   │   │   ├── interactions.py# REST CRUD — structured-form path
│   │   │   └── hcps.py        # HCP search/create ("Search or select HCP...")
│   │   ├── config.py, database.py, models.py, schemas.py, llm.py, main.py
│   └── requirements.txt, .env.example
└── frontend/
    ├── src/
    │   ├── components/        # LogInteractionScreen, InteractionForm, ChatPanel, FollowUpSuggestions
    │   ├── store/              # Redux slices: interactionsSlice, chatSlice
    │   └── api/client.js
    └── package.json
```

## Why this architecture

Both the form and the chat panel write through the **same tool functions**
(`app/agent/tools.py`), so a rep can start logging an interaction by typing in
chat and finish by editing fields in the form (or vice versa) without the two
surfaces drifting out of sync. The REST endpoints call the tools directly for
deterministic form submissions; the chat endpoint routes through the LangGraph
agent, which decides *which* tool a free-text message implies.

## The LangGraph agent's role

The agent is the reasoning layer behind the "AI Assistant" chat panel. Its job
is to turn a rep's unstructured, conversational note ("Met Dr. Sharma, discussed
OncoBoost efficacy data, she seemed positive, left a sample") into the correct
CRM action, without the rep ever touching a form field. Concretely it:

1. **Classifies intent** — a `classify_intent` node calls the LLM in JSON mode
   to decide whether the message is a new interaction to log, an edit to an
   existing one, a request for an HCP's interaction history, a request for
   AI-suggested follow-ups, or a materials/sample lookup — and extracts the
   arguments each case needs.
2. **Routes to a tool node** — LangGraph's conditional edges dispatch to one
   of the 5 tool nodes below, each of which runs real DB reads/writes.
3. **Keeps state across the turn** — `AgentState` threads the session id,
   the resolved `interaction_id`, and which tools fired through the graph, so
   a follow-up message like "actually make that neutral, not positive" can
   resolve to "the interaction I just logged" without the rep repeating
   themselves.
4. **Produces a natural-language reply** — a final `respond` node turns the
   tool's structured result into the chat bubble text shown to the rep, while
   the full structured payload also flows back to Redux so the form panel
   updates live.

This mirrors how a rep would actually work: talk naturally, and have the CRM
turn that into a properly structured, queryable record — while still
supporting the structured form for reps who prefer precise field entry.

## The 5 tools

1. **`log_interaction`** *(mandatory)* — Captures a new interaction. When
   called from the chat panel with free text, it first calls the LLM
   (`gemma2-9b-it`) with an entity-extraction prompt to pull out HCP name,
   interaction type, topics discussed, materials/samples mentioned, sentiment,
   outcomes, and follow-ups as JSON, then creates the HCP record if new and
   inserts the `Interaction` row. When called from the structured form, the
   already-structured fields are used directly (no LLM call needed).
2. **`edit_interaction`** *(mandatory)* — Modifies an already-logged
   interaction. Resolves the target record either by an explicit
   `interaction_id` or by "the most recent interaction with `<hcp_name>`" when
   the rep refers to it conversationally. If the edit itself is phrased as
   free text ("she also asked for the dosing guide"), the LLM diffs it against
   the current record and returns only the fields that should change, which
   are then merged in — logged data is never blindly overwritten.
3. **`get_interaction_history`** — Looks up prior interactions for an HCP so
   a rep can ask "what did we last discuss with Dr. Rao?" before a meeting,
   and so `suggest_followups` has context to reason over.
4. **`suggest_followups`** — Given the latest interaction plus recent history
   for that HCP, asks the LLM for three concrete next-best-actions (e.g.
   schedule a follow-up, send a specific leaflet, add to an advisory board
   list) — this powers the "AI Suggested Follow-ups" list under Follow-up
   Actions in the form.
5. **`search_materials`** — Searches the marketing materials / sample catalog
   so the rep (or the chat agent, mid-conversation) can find the right item
   to attach as "Materials Shared" or "Samples Distributed."

## Groq model strategy

`app/llm.py` calls `gemma2-9b-it` by default for speed/cost on short
extraction and summarization tasks, and automatically retries on
`llama-3.3-70b-versatile` if the primary model call fails (rate limit /
transient error), giving the agent a stronger-reasoning fallback without the
caller needing to handle retries itself.

## Setup

### 1. Database

Create a Postgres (or MySQL) database and update `DATABASE_URL` in `.env`
(see `backend/.env.example`). Tables are auto-created on startup for this
assignment; a production build would use Alembic migrations instead.

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # then fill in GROQ_API_KEY and DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs` once running.

### 3. Frontend

```bash
cd frontend
npm install
echo "REACT_APP_API_BASE_URL=http://localhost:8000" > .env
npm start
```

Opens at `http://localhost:3000`.

## Trying it out

- **Form path**: fill in the left panel and click "Log Interaction."
- **Chat path**: type something like *"Met Dr. Sharma, discussed OncoBoost
  Phase III data, she was positive, left a sample pack"* into the AI
  Assistant panel and press Log — the agent extracts structured fields and
  creates the record.
- Ask *"what did we discuss with Dr. Sharma last time?"* to exercise
  `get_interaction_history`, or *"suggest follow-ups"* to exercise
  `suggest_followups`, or *"find OncoBoost materials"* to exercise
  `search_materials`.
- Follow up with *"actually change the sentiment to neutral"* to exercise
  `edit_interaction` against the interaction just logged.

## Notes / assumptions

- Groq API keys are per-user secrets — none are committed; create your own at
  console.groq.com and put it in `backend/.env`.
- The materials/sample catalog in `search_materials` is a small in-memory
  stand-in; a production build would back it with its own table.
- Voice-note summarization ("Summarize from Voice Note") is out of scope for
  this text-based reference implementation but would slot in as a 6th tool
  calling a speech-to-text step ahead of the same extraction prompt used in
  `log_interaction`.
