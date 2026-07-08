# AI School ERP Assistant

FastAPI implementation of an agentic School ERP assistant. It accepts natural language chat requests, plans ERP tool calls, executes those tools against mock data, remembers conversation context, writes structured logs, and returns structured JSON responses.

## Documentation Deliverables

- [Architecture diagram and complete project structure](ARCHITECTURE.md)
- [API documentation with Swagger/OpenAPI usage](API_DOCUMENTATION.md)
- [Static OpenAPI contract](openapi.json)
- Browser Swagger UI after startup: `http://127.0.0.1:8000/docs`
- Browser ReDoc after startup: `http://127.0.0.1:8000/redoc`

## Submission Checklist

This repository includes the requested project deliverables:

| Deliverable | File or URL |
| --- | --- |
| README with setup instructions | `README.md` |
| Architecture diagram and complete structure | `ARCHITECTURE.md` |
| API documentation | `API_DOCUMENTATION.md` |
| Swagger/OpenAPI UI | `/docs`, `/redoc`, `/openapi.json` after startup |
| Static OpenAPI export | `openapi.json` |
| Manual API examples | `api_examples.http`, `postman_collection.json` |

## Features

- `POST /chat` for natural language ERP questions
- `GET /chat/history` for persisted conversation history
- Agent planning before execution
- LLM provider abstraction for Ollama, OpenAI, Gemini, and disabled offline mode
- Tool registry with attendance, marks, fees, homework, timetable, academic summary, and recommendations
- Multi-step execution for compound questions
- Conversation memory for follow-up questions
- User-scoped conversation history and execution logs
- Browser history loading for the selected ERP user and student
- Attendance target insights
- Exam preparation planner
- Parent progress report
- SQLite runtime store seeded from `mock_data/*.json`
- Structured JSON logging in `logs/assistant.log`
- Graceful error responses for empty input, invalid students, invalid queries, missing records, tool failures, and unexpected exceptions
- Test coverage for APIs, services, planner behavior, logging, mock data validity, and hardcoded data audit

## Setup Instructions

### Quick Start

```powershell
cd F:\IR3\school-ai-assistant
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
$env:LLM_PROVIDER = "disabled"
python -m app.utils.seed_db
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open these URLs:

- App UI: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Raw OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

If port `8000` is blocked, use `--port 8002` and replace `8000` with `8002` in the URLs.

### 1. Prerequisites

- Python 3.11 or newer
- PowerShell or a compatible terminal
- Optional: Docker Desktop for containerized execution
- Optional: Ollama, OpenAI, or Gemini if you want LLM-generated wording instead of offline fallback responses

```bash
cd school-ai-assistant
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. Choose LLM Mode

The app defaults to Ollama. It also supports OpenAI, Gemini, and a disabled offline mode. Never put real API keys in `.env.example`; set them in your shell or a private `.env` file.

Offline/demo mode:

```powershell
$env:LLM_PROVIDER = "disabled"
```

Local Ollama mode:

```bash
ollama serve
ollama pull llama3.1
```

```powershell
$env:LLM_PROVIDER = "ollama"
```

Gemini mode:

```powershell
$env:LLM_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "your-private-key"
$env:GEMINI_MODEL = "gemini-2.5-flash"
```

OpenAI mode:

```powershell
$env:LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "your-private-key"
```

If a provider fails, the assistant still works through the deterministic ERP planner and shows fallback status in the chat output.

### 3. Seed the Database

The application auto-seeds on startup when `AUTO_SEED=true`, but you can seed manually:

```bash
python -m app.utils.seed_db
```

### 4. Start the API

Default local server:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If port `8000` is blocked, use another port:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Or start the local offline demo helper:

```powershell
.\scripts\start_local_server.ps1
```

### 5. Open the App

- Browser chat UI: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
- ReDoc docs: `http://127.0.0.1:8000/redoc`
- Readiness checklist: `GET http://127.0.0.1:8000/readiness`
- Chat endpoint: `POST http://127.0.0.1:8000/chat`
- Conversation sessions: `GET http://127.0.0.1:8000/chat/conversations`
- Health endpoint: `GET http://127.0.0.1:8000/health`
- Tool manifest endpoint: `GET http://127.0.0.1:8000/tools`
- Student list endpoint: `GET http://127.0.0.1:8000/students`
- User list endpoint: `GET http://127.0.0.1:8000/users`
- Execution logs endpoint: `GET http://127.0.0.1:8000/logs`

If you started the server on port `8002`, replace `8000` with `8002` in all URLs.

## Demo Login

The browser UI opens with a login screen. Demo credentials are loaded from `mock_data/users.json` and seeded into SQLite.

| Login Type | User ID | Password |
| --- | --- | --- |
| Teacher | `U_TEACHER_10A` | `teacher10a` |
| Parent / Student | `U_STUDENT_001` | `student001` |

## Docker

Run the app with Docker Compose:

```bash
docker compose up --build
```

The container defaults to `LLM_PROVIDER=disabled`, so it can be evaluated without external API keys. To use Ollama from the host:

```bash
set LLM_PROVIDER=ollama
docker compose up --build
```

The SQLite database and logs are stored in the `school_ai_data` Docker volume.

## Demo Script

With the API running, execute:

```powershell
.\scripts\demo_requests.ps1
```

The script checks health, runs a multi-step chat request, verifies conversation-memory follow-up, and prints execution logs.

## API Examples

Use `api_examples.http` with VS Code REST Client, JetBrains HTTP Client, or a compatible REST tool. It includes health, metadata, multi-step chat, memory follow-up, bonus feature requests, history, and logs.

Use `postman_collection.json` if you prefer Postman. It covers the same evaluator flow and stores the first chat response's `conversation_id` as a collection variable for the memory follow-up request.

Use `openapi.json` for a static API contract. Regenerate it after API changes with:

```bash
python scripts/export_openapi.py
```

Full endpoint notes and Swagger/OpenAPI instructions are in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

Requests may pass either `user_id` in the JSON/query parameters or an `X-ERP-Auth-Token` header. Demo tokens are stored in `mock_data/users.json`; if both are provided, they must resolve to the same ERP user.

The browser UI also includes an optional Auth Token field. When it is filled, requests use `X-ERP-Auth-Token` and omit `user_id`.

Example request:

```json
{
  "student_id": "S001",
  "message": "Show my attendance, Mathematics marks, and pending fees.",
  "return_plan": true
}
```

Example token-authenticated request:

```text
X-ERP-Auth-Token: token-student-001
```

```json
{
  "student_id": "S001",
  "message": "Show my marks.",
  "return_plan": true
}
```

Example history request:

```text
GET /chat/history?student_id=S001&limit=20
```

Example conversation list request:

```text
GET /chat/conversations?student_id=S001&limit=20
```

## Configuration

Copy `.env.example` into your environment or set these variables directly:

```text
DATABASE_URL=sqlite:///school_erp.db
LLM_PROVIDER=ollama
LLM_TEMPERATURE=0
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
OLLAMA_TIMEOUT_SECONDS=2
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=10
GEMINI_API_KEY=
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=10
APP_TIMEZONE=Asia/Calcutta
LOG_FILE_PATH=logs/assistant.log
MOCK_DATA_DIR=mock_data
AUTO_SEED=true
```

Provider examples:

```bash
set LLM_PROVIDER=openai
set OPENAI_API_KEY=your-key
```

```bash
set LLM_PROVIDER=gemini
set GEMINI_API_KEY=your-key
```

## Verification

```bash
python -m compileall app tests
python scripts/export_openapi.py
python -m pytest -q
python -m pytest --cov=app --cov-fail-under=90
ruff check .
docker compose config --quiet
```

The coverage gate currently enforces at least 90% application coverage. The hardcoding audit checks that application code does not embed mock student records, fixed dates, sample percentages, or canned assignment phrases. ERP data belongs in `mock_data/` and is loaded into SQLite through the seed command.

## Architecture

For the full architecture diagram, request flow, component map, database tables, and complete directory structure, see [ARCHITECTURE.md](ARCHITECTURE.md).

- `app/api/`: FastAPI routes
- `app/agents/`: LLM provider, planner, executor, response generation
- `app/services/`: SQLite-backed ERP query services
- `app/tools/`: Tool manifest and registry
- `app/memory/`: Conversation history persistence
- `app/models/`: Pydantic API schemas
- `app/utils/`: Config, date helpers, seed command, logging, errors
- `mock_data/`: Source data for the mock ERP
- `tests/`: Verification suite
