# SATHEE Guidance AI Agent — v1 Prototype

A conversational agent that helps students and well-wishers discover and use
[SATHEE](https://sathee.iitk.ac.in), IIT Kanpur's free JEE/NEET prep platform:
onboarding, study planning, resource recommendations, basic doubt support,
and a well-wisher mode.

This is a runnable local prototype matching the architecture in the project
brief: **Chat UI → FastAPI backend → OpenAI LLM + Knowledge Base + Session store.**

```
sathee-agent/
├── backend/
│   ├── main.py            FastAPI app (serves API + frontend)
│   ├── agent.py           System prompt, OpenAI call, profile extraction
│   ├── knowledge_base.py  SATHEE facts, links, forwardable message
│   ├── session_store.py   In-memory conversation + profile store
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── index.html         Single-file chat UI (no build step)
```

## 1. Setup

```bash
cd sathee-agent/backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and paste your OpenAI API key:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## 2. Run

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser — that's the chat UI, served
directly by the backend.

## 3. How it works

- **`knowledge_base.py`** holds the SATHEE facts (links, exams covered,
  features, the forwardable well-wisher message, and safety rules like
  "never ask for money"). This is injected into every system prompt so the
  agent never invents facts.
- **`session_store.py`** keeps a per-browser conversation history and a
  small profile (student/well-wisher, exam, class, language, study hours,
  weak/strong subjects) — held in memory, so it resets when the server
  restarts. A session id is generated on first message and saved in the
  browser's `localStorage`, so refreshing the page keeps your conversation.
- **`agent.py`** builds the system prompt from the KB + known profile,
  calls OpenAI, and uses a `update_user_profile` tool so the model can
  save new facts about the user as they come up naturally in chat
  (instead of forcing a rigid form).

This intentionally follows the brief's flows loosely rather than a strict
state machine — a real conversation branches, and the system prompt gives
the model enough structure (ask user type → explain SATHEE → registration →
study plan / resources / doubts, or well-wisher script) to follow the
intended flow without feeling scripted.

## 4. Suggested next steps

Roughly in the order they'll matter:

1. **Test it end-to-end** with a few real conversations as both a student
   and a well-wisher persona; tighten the system prompt in `agent.py` based
   on what goes wrong.
2. **Persist sessions** — swap `session_store.py`'s in-memory dict for
   SQLite (schema: `sessions(id, profile_json, created_at)`,
   `messages(session_id, role, content, created_at)`) so profiles/history
   survive a restart.
3. **Expand the knowledge base** — right now it's hand-written facts; if
   you want the agent to answer very specific questions (e.g. "which exact
   chapter is DPP #14?"), you'll want real SATHEE content indexed (start
   simple: a JSON list of {topic, resource_link}; move to embeddings/RAG
   only if the KB gets large).
4. **Guardrail testing** — deliberately try to get the agent to ask for
   money, guarantee a rank, or go off-topic, and adjust the system prompt/
   rules until it reliably refuses.
5. **Deploy** — once you're happy locally, Render/Railway (backend) +
   your domain or a free static host (frontend) get this live cheaply.
   WhatsApp/Telegram bots can be added as another endpoint that calls the
   same `agent.get_reply()` function.
6. **Multi-language** — the system prompt already tells the model to match
   the user's language; test Hindi and a couple of regional languages
   specifically, since that's core to reaching the target users.

## 5. Cost note

`gpt-4o-mini` is used by default to keep this cheap to run/test. You can
change `OPENAI_MODEL` in `.env` at any time.
