# SATHEE Guidance Agent - Project Status

This document records the current implementation, technology choices, completed
work, configuration, and remaining work for the SATHEE Guidance Agent.

## 1. Project purpose

SATHEE is a student study companion for JEE Main, JEE Advanced, and NEET
preparation. It provides:

- An AI chat assistant grounded in SATHEE knowledge and local study resources.
- Deterministic, date-based study-plan generation.
- Student email registration and login.
- Per-student chat-history and study-profile persistence.
- A browser-based chat and study-plan interface served by the backend.

## 2. Current completion status

### Completed

- Single-process FastAPI application serving both API and frontend.
- Gemini integration through Google's OpenAI-compatible API.
- Tool-calling agent for:
  - Updating exam type and exam date.
  - Generating a study plan.
  - Looking up a plan entry for a requested date.
- Local RAG retrieval using SATHEE facts and files in `backend/knowledge/`.
- JEE Main, JEE Advanced, and NEET syllabus data.
- Exact day-by-day study-plan generation from the current date to the exam date.
- Phase allocation: Foundation, Coverage, Rapid Revision, Revision, Practice &
  Mocks, Final Sprint, and Final Revision.
- Every syllabus topic is assigned to a visible plan day, including short
  timelines where multiple topics share a day.
- Email registration and login.
- Case-insensitive unique email addresses.
- Password validation requiring at least eight characters.
- Salted `scrypt` password hashing; plaintext passwords are not stored.
- Authentication enforcement for chat, history, reset, and study-plan APIs.
- Chat history restoration after login.
- Student profile icon showing email and current study details.
- Persistent conversation list with multiple chats per student.
- New-chat creation and reopening of previous conversations.
- SQLite conversation/message storage with ownership checks.
- SQLite conversation messages are the authoritative per-chat history; the
  selected chat is loaded into the agent context before every reply.
- Conversation titles derived from the first student message.
- Practice-result recording with accuracy-based review recommendations.
- Study-plan adjustment tool for missed days or exam-date changes.
- Refined responsive chat UI with profile and progress details.
- SQLite account database.
- Optional Pinecone persistence for chat messages and study profiles.
- Automatic Pinecone serverless index creation when configured.
- Local fallback to in-memory sessions when Pinecone is not configured.
- Login page and single-page chat/study-plan UI with plain HTML, CSS, and
  JavaScript.
- Validation completed for:
  - Python syntax and compilation.
  - Study-plan topic coverage.
  - Duplicate-email rejection.
  - Password hashing and login.
  - Authenticated and unauthenticated API access.
  - Chat-history retrieval.

### Known current limitations

- Gemini API availability depends on the configured API key and quota. A
  quota-exhausted Gemini key returns an upstream `429` error.
- The default UI uses browser `localStorage` for the session ID.
- The current session token is a long-lived database value; production should
  replace it with expiring, revocable tokens or secure HTTP-only cookies.
- There is no email verification, password reset, logout endpoint, rate
  limiting, or account lockout yet.
- SQLite is suitable for the current single-service setup; a production
  deployment may need PostgreSQL or another managed relational database.
- The Pinecone implementation stores chat content as vector metadata and uses
  deterministic hash embeddings. It is persistence-oriented, not intended as
  the primary semantic RAG index.
- No automated test suite is committed yet; current checks are focused smoke
  tests and syntax validation.

## 3. Technology stack

### Backend

- Python
- FastAPI - HTTP API and application server
- Uvicorn - ASGI development/production server
- Pydantic - request-model validation
- `python-dotenv` - `.env` configuration loading
- SQLite - student account records
- Python `hashlib.scrypt` and `hmac` - password hashing and verification
- OpenAI Python SDK - Gemini OpenAI-compatible API client
- Pinecone Python SDK - optional durable session/profile/chat storage

### AI and retrieval

- Google Gemini model configured through `OPENAI_MODEL`
- Google Generative Language OpenAI-compatible endpoint
- Local token-overlap and IDF-weighted retrieval in `rag_pipeline.py`
- Deterministic Python study-plan generation in `study_plan.py`

### Frontend

- Static HTML
- CSS
- Browser JavaScript using `fetch`
- Browser `localStorage` for the current authenticated session ID
- No frontend framework or separate frontend build step

## 4. Repository structure

```text
SATHEE_project/
├── README.md
├── PROJECT_STATUS.md
├── .gitignore
└── backend/
    ├── main.py
    ├── agent.py
    ├── auth.py
    ├── knowledge_base.py
    ├── pinecone_store.py
    ├── rag_pipeline.py
    ├── session_store.py
    ├── study_plan.py
    ├── syllabus_data.py
    ├── requirements.txt
    ├── .env
    ├── .env.example
    ├── sathee_auth.db
    ├── knowledge/
    │   └── README.md
    └── static/
        └── index.html
```

## 5. Main files and responsibilities

### `backend/main.py`

Creates the FastAPI application, defines API request models, enforces
authentication, serves the static frontend, and exposes chat, history,
study-plan, reset, login, and registration endpoints.

### `backend/agent.py`

Runs the Gemini conversation loop. It sends the system prompt, retrieved local
context, conversation history, and tool definitions to Gemini. Tool calls update
the student profile or generate/look up a deterministic study plan.

### `backend/auth.py`

Creates and accesses the SQLite `users` table. It:

- Normalizes email addresses to lowercase.
- Enforces unique emails using SQLite `UNIQUE COLLATE NOCASE`.
- Hashes passwords with a random salt and `scrypt`.
- Verifies passwords with constant-time comparison.
- Issues the current session ID used by protected endpoints.

### `backend/session_store.py`

Maintains the in-memory session cache and the public session-store functions.
It stores a maximum rolling history of 40 messages and delegates persistence
to `pinecone_store.py` when Pinecone is enabled.

### `backend/conversation_store.py`

Stores conversation metadata and messages in SQLite. Conversations are linked
to the authenticated student's email, listed in recency order, and checked
for ownership before history is returned or a message is added.

### `backend/pinecone_store.py`

Optionally creates and uses a Pinecone serverless index. It stores:

- Non-sensitive exam profile values.
- Study plans.
- Chat messages and metadata.

It must not be used to store passwords, API keys, access tokens, or other
authentication secrets.

### `backend/rag_pipeline.py`

Loads built-in SATHEE facts and `.md`/`.txt` files from `backend/knowledge/`,
splits them into chunks, calculates IDF-weighted token overlap, and returns
retrieved context for the AI agent.

### `backend/study_plan.py`

Calculates exact dates and phase durations. It prioritizes topics by syllabus
weightage and assigns every topic to a concrete plan day.

### `backend/syllabus_data.py`

Contains the current JEE Main, JEE Advanced, and NEET subject/topic lists,
approximate topic weightages, and free SATHEE/NCERT resource references.

### `backend/knowledge_base.py`

Contains SATHEE facts, the agent's behavior instructions, and system-prompt
construction using the student's current profile and retrieved context.

### `backend/static/index.html`

Provides:

- Registration and login forms.
- Chat interface.
- Study-plan tab.
- Chat-history loading after login.
- Session validation and expired-session handling.

## 6. API endpoints

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` | Create a student account |
| `POST` | `/api/auth/login` | Log in with email and password |
| `GET` | `/api/auth/session/{session_id}` | Validate an authenticated session |

Registration returns HTTP `409` when the email is already used. Login and
invalid-session requests return HTTP `401`.

### Chat and session

| Method | Endpoint | Authentication |
|---|---|---|
| `POST` | `/api/chat` | Required |
| `GET` | `/api/chat/history/{session_id}` | Required |
| `GET` | `/api/chat/conversations/{session_id}` | Required; list the student's chats |
| `POST` | `/api/chat/conversations/{session_id}` | Required; create a new chat |
| `POST` | `/api/reset` | Required |
| `GET` | `/api/session/new` | Legacy/public utility endpoint |

### Study plans and knowledge

| Method | Endpoint | Authentication |
|---|---|---|
| `GET` | `/api/study-plan/{session_id}` | Required |
| `GET` | `/api/study-plan/{session_id}/today` | Required |
| `GET` | `/api/knowledge/search?q=...&limit=...` | Public inspection endpoint |

### Frontend

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Serves the login/chat UI |
| `GET` | `/static/...` | Serves static assets |

## 7. Data storage

### SQLite account database

Default path:

```text
backend/sathee_auth.db
```

Override with:

```env
SATHEE_AUTH_DB=C:\path\to\sathee_auth.db
```

The `users` table contains:

- Internal numeric ID.
- Normalized email.
- Salted password hash.
- Session ID.
- Account creation timestamp.

### Pinecone session database

Pinecone is optional. When configured, the application creates the configured
serverless index and uses the configured namespace. Session vectors contain
profile or message metadata keyed by the authenticated session ID.

## 8. Configuration

Copy the example file on Windows:

```powershell
Set-Location backend
Copy-Item .env.example .env
```

Required:

```env
OPENAI_API_KEY=your-gemini-api-key
```

Optional model:

```env
OPENAI_MODEL=gemini-3.6-flash
```

Optional Pinecone:

```env
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=sathee-sessions
PINECONE_NAMESPACE=sathee
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
```

Never commit `backend/.env`, API keys, passwords, or other secrets.

## 9. Running the project

From the repository root:

```powershell
Set-Location backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000
```

Production deployment should use a secret manager, HTTPS, a managed database,
restricted CORS, expiring sessions, and a process manager.

## 10. User flow

1. A student opens the site.
2. The login page is shown unless a valid session exists in `localStorage`.
3. A new student registers with an email and password.
4. A returning student logs in with the same email and password.
5. The backend validates the session before chat, history, reset, or plan access.
6. Previous chat history is loaded into the chat view.
7. The profile icon shows the student's email and current exam details.
8. The student can create a new chat or reopen any previous chat.
9. The student tells the agent their exam and exam date.
10. The agent extracts profile data through a tool call.
11. After consent and complete exam details, the deterministic study-plan
   generator creates the plan.
12. The plan is available in the “My Study Plan” tab.
13. New messages and profile updates are persisted through the configured
    session store.

## 11. Recommended next steps

1. Add automated unit/API tests to CI.
2. Add logout and session revocation.
3. Use expiring secure HTTP-only cookies or short-lived signed tokens.
4. Add email verification and password reset.
5. Add rate limiting and account lockout protections.
6. Add structured error handling for Gemini quota and upstream failures.
7. Add migration/version management for the account database.
8. Move production accounts from SQLite to a managed relational database.
9. Add a dedicated semantic embedding strategy if Pinecone search is needed.
10. Expand and verify syllabus coverage against current official exam sources.
11. Add observability, backups, and privacy/data-retention controls.
