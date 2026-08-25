# SATHEE Guidance Agent

This is a **single FastAPI service** — there's no separate frontend
server to run. FastAPI serves both the JSON API and the chat UI
(plain HTML/JS, no build step) from the same process.

```
sathee-agent-v3/
└── backend/                 <- run everything from here
    ├── main.py              FastAPI app: API routes + serves static/
    ├── agent.py             Gemini calls + tool-calling logic
    ├── knowledge_base.py    SATHEE facts + system prompt
    ├── rag_pipeline.py      Local chunking, IDF retrieval, and source context
    ├── knowledge/            Add verified Markdown/text source documents here
    ├── session_store.py     In-memory session/profile store
    ├── study_plan.py        Day-by-day plan generator
    ├── syllabus_data.py     JEE/NEET syllabus reference data
    ├── requirements.txt
    ├── .env.example
    └── static/
        └── index.html       <- the chat UI (the "frontend")
```

## Run it

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# edit .env and put your Gemini API key in OPENAI_API_KEY
export $(cat .env | xargs)   # or use python-dotenv
uvicorn main:app --reload
```

## RAG pipeline

The agent uses a local, dependency-free retrieval pipeline. It chunks the
built-in SATHEE facts and every `.md`/`.txt` file in `backend/knowledge/`,
scores passages with IDF-weighted token overlap, and injects the top passages
into each model request with source labels. This keeps factual answers tied to
the material you provide without requiring a vector database.

To add content, place verified notes, official syllabus pages, or resource
guides in `backend/knowledge/` and restart the service. Inspect retrieval with:

```text
GET /api/knowledge/search?q=SATHEE%20practice%20tests
```

The deterministic planner remains separate from RAG: RAG grounds explanations
and resources, while Python computes exact day-by-day dates, topics, and daily
practice work.

Then open **http://localhost:8000** — that one URL serves the chat UI,
which calls the API routes on the same origin (`/api/chat`,
`/api/study-plan/{session_id}`, etc.). Nothing else to start.

If you'd prefer a genuinely separate frontend (its own dev server, a
framework like React, deployed to a different host than the API), that's
a different setup — say so and I'll restructure it that way instead.
