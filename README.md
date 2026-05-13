# 🤖 Autonomous Job Hunt AI Agent

Production-grade FastAPI backend for an **AI-powered autonomous job hunting agent**. The system follows an agentic loop — **Goal → Plan → Act → Observe → Repeat** — to search for jobs, tailor resumes & cover letters, prepare applications, and track their status, all orchestrated through a single API call. It also includes a structured **Career Recommendation Feature** for users who are unsure which role to pursue.

Built with request-safe concurrency, SQL-backed persistence, strict plan validation, structured error reporting, and retry-aware step execution.

---

## ✨ Key Guarantees

| Guarantee | Detail |
|---|---|
| **No in-memory state** | Plans, jobs, and applications are persisted in SQL — never held in singletons |
| **Hunt isolation** | Every request operates on its own `hunt_id`; concurrent hunts never share state |
| **Async end-to-end** | Async SQLAlchemy with `asyncpg` (PostgreSQL) or `aiosqlite` (tests) |
| **Strict plan validation** | Required steps, ordering, duplicates, and numbering are all validated before execution |
| **Stop-on-failure** | If any critical step fails, execution halts, the hunt is marked `failed`, and errors are returned |
| **Structured errors** | Every failure surfaces as a typed `ErrorDetail` with code, message, hunt context, and retry hint |
| **Configurable retries** | Transient step failures are retried up to `STEP_RETRY_ATTEMPTS` with exponential back-off |
| **Structured logging** | JSON logs with `hunt_id`, step name, latency, and failure details |
| **Adaptive strategy** | Application behavior is tracked, classified, and used to adjust future hunts |
| **ABC re-ranking loop** | Recommendations log antecedents, behaviors, and outcomes, then update user-specific strategy weights |

---

## 🏗️ Architecture

```text
                         ┌─────────────────┐
                         │    FastAPI App   │
                         │   (main.py)      │
                         └───────┬─────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     API Layer (api/)     │
                    │  routes · schemas · deps │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Service Layer          │
                    │  hunt_service · validator │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │        Orchestrator (runner.py)       │
              │ recommend? → plan → search → apply → track │
              └──────┬────┬────┬────┬────┬──────────┘
                     │    │    │    │    │
         ┌───────────▼─┐    ┌─▼──┐    ┌─▼──────────┐
         │ Career +    │    │Job │    │  Resume /   │
         │ Planner     │    │Find│    │ Cover Letter│
         │ Agents      │    └────┘    └─────────────┘
         └─────────────┘
                                           │
                              ┌────────────▼──────┐
                              │  Application      │
                              │  Agent + Tracker   │
                              └───────────────────┘
                                       │
                          ┌────────────▼────────────┐
                          │   Storage Layer          │
                          │  database · repository   │
                          │  records (ORM)           │
                          └──────────────────────────┘
```

### Agentic Loop

1. **Goal** — User submits a job goal (e.g., *"Backend Engineer"*) or a partial profile.
2. **Recommend (optional)** — If the goal is vague or missing, the Career Agent recommends suitable roles and the top role becomes the refined goal.
3. **Plan** — Planner agent calls the LLM to produce a 4-step execution plan.
4. **Act** — Each step is executed in sequence: search → apply → track.
5. **Observe** — Results are persisted and validated after each step.
6. **Repeat / Halt** — On failure the system retries (configurable) or halts with a structured error.

---

## 📁 Project Structure

```text
backend/
├── main.py                  # Application factory + uvicorn entrypoint
├── api/
│   ├── dependencies.py      # Request-scoped DB session + service wiring
│   ├── errors.py            # JSON exception handlers
│   ├── routes.py            # HTTP endpoints
│   └── schemas.py           # Request/response envelopes
├── agents/
│   ├── __init__.py          # AgentSuite dataclass
│   ├── career_agent.py      # LLM-driven career recommendations
│   ├── planner.py           # LLM-driven plan generation
│   ├── job_finder.py        # Scraper + parser orchestration
│   ├── resume_agent.py      # Tailored resume generation (LLM)
│   ├── cover_letter_agent.py # Tailored cover letter generation (LLM)
│   ├── apply_agent.py       # Application assembly
│   └── tracker_agent.py     # Tracker projection
├── core/
│   ├── config.py            # Immutable Settings dataclass + env parsing
│   ├── llm.py               # OpenAI JSON client wrapper
│   └── logger.py            # Structured JSON logging
├── models/
│   ├── application.py       # Application + tracker models
│   ├── abc.py               # ABC recommendation, behavior, outcome, and strategy models
│   ├── career.py            # UserProfile + career recommendation models
│   ├── errors.py            # Structured ErrorDetail model
│   ├── hunt.py              # Hunt lifecycle models (HuntResult)
│   ├── job.py               # Job models
│   └── plan.py              # ExecutionPlan + StepType models
├── orchestrator/
│   └── runner.py            # Step execution with stop-on-failure + retries
├── services/
│   ├── analytics_service.py  # Application metrics and performance reports
│   ├── abc_service.py        # ABC-driven adaptive recommendation and re-ranking
│   ├── behavior_service.py   # Deterministic behavior classification
│   ├── exceptions.py        # Domain exceptions with HTTP status mapping
│   ├── hunt_service.py      # API-facing service layer
│   ├── plan_validator.py    # Strict plan validation rules
│   ├── strategy_service.py  # Behavior-aware hunt strategy adjustments
│   └── tracking_service.py  # Behavior snapshot persistence
├── storage/
│   ├── database.py          # Async engine + session factory
│   ├── records.py           # SQLAlchemy ORM table definitions
│   └── repository.py        # Hunt persistence and retrieval
├── tools/
│   ├── parser.py            # Raw scrape → Job conversion
│   └── scraper.py           # Live scrape + deterministic fallback
└── memory/                  # (reserved for future context/memory features)

tests/
├── test_abc_adaptive.py     # Closed-loop ABC re-ranking tests
├── test_api.py              # Full API integration tests
└── test_plan_validation.py  # Planner validation unit tests
```

---

## 📊 Data Model

| Table | Purpose | Key |
|---|---|---|
| `hunts` | One row per request, tracks lifecycle status | `hunt_id` |
| `plans` | One plan snapshot per hunt | `hunt_id` FK |
| `jobs` | Job listings discovered during search | `hunt_id` FK |
| `applications` | Prepared applications plus behavior tracking fields | `hunt_id` FK |
| `behavior_metric_snapshots` | Stored derived behavior metrics over time | `user_key` |
| `recommendation_events` | Antecedent records explaining why jobs were shown | `user_id`, `hunt_id`, `job_id` |
| `behavior_events` | User actions linked to a specific recommendation context | `antecedent_event_id` FK |
| `outcomes` | Consequences linked to behavior events | `behavior_event_id` FK |
| `user_strategy_profiles` | Learned per-user category weights and rates | `user_id` |

All reads and writes are scoped by `hunt_id`, so simultaneous hunts are fully isolated.
Behavior analytics are scoped by `user_key`, which comes from `X-User-Id` when supplied, then falls back to the caller IP.
ABC recommendation learning is scoped by `user_id`; two users with different outcomes can receive different rankings for the same candidate jobs.

---

## 🔄 Execution Workflow

```text
POST /api/v1/hunts { "goal": "Backend Engineer" }
         │
         ▼
  ┌─ 1. Create Hunt row ──────────────────────────────┐
  │  2. Career Agent (optional) → refine vague goals   │
  │  3. Planner Agent → LLM → ExecutionPlan            │
  │  4. Validate plan (steps, order, duplicates)       │
  │  5. Search Agent → scrape/fallback → persist jobs  │
  │  6. Per-job: Resume Agent + Cover Letter Agent     │
  │  7. Application Agent → assemble & persist         │
  │  8. Tracker Agent → build tracker entries          │
  │  9. Mark hunt completed                            │
  └────────────────────────────────────────────────────┘
         │
         ▼
  Return full HuntResult with plan, jobs, applications, tracker
```

If any critical step fails, execution stops immediately, the hunt is marked `failed`, and the API returns `success: false` with structured error details.

---

## 🌐 API Reference

All endpoints are prefixed with `/api/v1` (configurable via `API_PREFIX`).

Interactive docs are available at:
- **Swagger UI** → `http://localhost:8000/docs`
- **ReDoc** → `http://localhost:8000/redoc`

### Health Check

```
GET /api/v1/health
```

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "version": "2.0.0"
  },
  "errors": []
}
```

### Start a Hunt

```
POST /api/v1/hunts
```

**Request body:**

```json
{
  "goal": "Backend Engineer"
}
```

You can also send a vague goal with profile context:

```json
{
  "goal": "not sure",
  "skills": ["Python", "APIs"],
  "interests": ["building systems"]
}
```

**Success response:**

```json
{
  "success": true,
  "data": {
    "hunt_id": "5a570e5f-4638-4a4f-b9f1-77302f405f3f",
    "goal": "Backend Engineer",
    "original_goal": null,
    "career_recommendation": null,
    "goal_was_recommended": false,
    "status": "completed",
    "plan": {
      "goal": "Backend Engineer",
      "summary": "Search, tailor, and track applications",
      "steps": [
        {"step_number": 1, "step_type": "plan",   "description": "Confirm strategy",      "parameters": {}},
        {"step_number": 2, "step_type": "search", "description": "Search matching roles",  "parameters": {"query": "Backend Engineer", "location": "India", "max_results": 1}},
        {"step_number": 3, "step_type": "apply",  "description": "Prepare applications",   "parameters": {}},
        {"step_number": 4, "step_type": "track",  "description": "Track applications",     "parameters": {}}
      ]
    },
    "jobs_found": [ ... ],
    "applications": [ ... ],
    "tracker": [ ... ],
    "created_at": "2026-04-19T10:00:00Z",
    "completed_at": "2026-04-19T10:00:02Z",
    "summary": {
      "total_jobs": 1,
      "total_applications": 1,
      "tracked_applications": 1,
      "error_count": 0
    }
  },
  "errors": []
}
```

### Recommend a Career

```
POST /api/v1/recommend-career
```

**Request body:**

```json
{
  "skills": ["Python", "APIs"],
  "interests": ["building systems"]
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "recommended_roles": [
      {
        "role": "Backend Developer",
        "reason": "Based on Python and API-oriented systems interests",
        "required_skills": ["Python", "FastAPI", "Databases"]
      },
      {
        "role": "API Engineer",
        "reason": "Strong fit for service and integration design work",
        "required_skills": ["REST APIs", "Python", "System Design"]
      },
      {
        "role": "Software Engineer",
        "reason": "Broad engineering potential with backend alignment",
        "required_skills": ["Programming", "Problem Solving", "Systems Thinking"]
      }
    ]
  },
  "errors": []
}
```

## 🧭 Career Recommendation Feature

This feature exists for users who are unsure about their job target. Instead of forcing an ambiguous goal into the normal pipeline, the backend first asks the Career Agent to analyze the user profile and recommend the most suitable roles.

Where it fits in the pipeline:
- `POST /api/v1/recommend-career` provides direct structured role suggestions from a partial profile.
- `POST /api/v1/hunts` reuses the same agent automatically when the submitted goal is vague or missing.
- The top recommendation becomes the refined goal passed to the Planner Agent.
- The hunt response includes the structured recommendation payload and whether the final goal was auto-selected.

## 📈 Behavior Analysis and Adaptive Strategy

The behavior engine turns application history into deterministic strategy changes. Every prepared application stores the role, company, platform, resume version, applied timestamp, outcome status, and referral flag. After the apply step, the backend recomputes and stores a behavior snapshot.

Tracked metrics:
- `apps_per_day`
- `success_rate`
- `platform_distribution`
- `role_diversity`
- `resume_success_rate`
- `referral_ratio`

Classifications:
- `insufficient_data`
- `hardcore`
- `mass_applier`
- `passive`
- `desperate`
- `networker`

Where it fits in `/hunts`:
- Before search/apply, the orchestrator loads metrics for the current `user_key`.
- The behavior service classifies the user using fixed thresholds and a minimum sample size.
- The strategy service adjusts job selection, max application count, fit threshold, resume version, referral bias, and role similarity rules.
- After applications are persisted, a fresh metric snapshot is stored.

### Behavior Profile

```
GET /api/v1/behavior-profile
```

Use `X-User-Id` to scope behavior to a user:

```bash
curl http://localhost:8000/api/v1/behavior-profile \
  -H "X-User-Id: user-123"
```

### Current Strategy

```
GET /api/v1/strategy
```

Returns the active strategy adjustments and why they were chosen.

### Analytics

```
GET /api/v1/analytics
```

Returns the performance breakdown used by the behavior engine.

## 🧠 ABC-Driven Adaptive Recommendation Engine

The ABC engine creates a closed learning loop:

```text
Antecedent: job shown → Behavior: user acts → Consequence: outcome arrives
        → Strategy weights update → Future jobs are re-ranked differently
```

This is separate from a dashboard. Every ranked job stores the reason it was shown, the scores used, filters applied, and the exact strategy weights active at that moment. Later behavior and outcomes must link back to that recommendation event, so learning always has context.

What it learns per user:
- Category weights for `backend`, `frontend`, `data`, `devops`, `mobile`, and `general`.
- Click, application, abandonment, success, rejection, no-response, offer, follow-up, resume-performance, and response-time signals.
- Time-decayed scores so recent outcomes influence rankings more than old history.
- Smoothed confidence so sparse data does not overfit after one bad result.

Where it fits in `/hunts`:
- Search produces candidate jobs.
- Existing behavior strategy filters jobs first.
- ABC re-ranks the remaining jobs before applications are generated.
- Each returned job includes `ranking_position`, `base_match_score`, `final_score`, `recommendation_reason`, `recommendation_event_id`, and `job_category`.

### Rank Candidate Jobs

```
POST /api/v1/abc/recommendations
```

**Request body:**

```json
{
  "user_id": "user-123",
  "hunt_id": "hunt-001",
  "session_id": "session-001",
  "goal": "Software Engineer",
  "filters": {
    "remote_only": true
  },
  "jobs": [
    {
      "job_id": "backend-job",
      "title": "Software Engineer",
      "company": "Backend Systems Co",
      "location": "Remote",
      "description": "Build backend APIs, databases, and platform services.",
      "requirements": ["software", "api", "backend", "database"],
      "source": "manual"
    },
    {
      "job_id": "frontend-job",
      "title": "Software Engineer",
      "company": "Frontend Product Co",
      "location": "Remote",
      "description": "Build frontend React UI and product workflows.",
      "requirements": ["software", "react", "frontend", "ui"],
      "source": "manual"
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "user_id": "user-123",
    "hunt_id": "hunt-001",
    "session_id": "session-001",
    "recommendations": [
      {
        "event_id": "rec_abc",
        "job_id": "backend-job",
        "rank": 1,
        "job_category": "backend",
        "base_match_score": 0.81,
        "behavior_score": 0.44,
        "outcome_score": 0.73,
        "category_weight": 0.74,
        "final_score": 0.69,
        "reason": "Strong backend interview and offer history",
        "strategy_weights": {
          "backend": 0.74,
          "frontend": 0.42
        },
        "filters": {
          "remote_only": true
        }
      }
    ]
  },
  "errors": []
}
```

### Log Behavior

```
POST /api/v1/abc/behavior-events
```

**Request body:**

```json
{
  "antecedent_event_id": "rec_abc",
  "event_type": "application_completed",
  "resume_id": "resume-v2"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "event_id": "behavior_456",
    "antecedent_event_id": "rec_abc",
    "user_id": "user-123",
    "hunt_id": "hunt-001",
    "session_id": "session-001",
    "event_type": "application_completed",
    "job_id": "backend-job",
    "resume_id": "resume-v2",
    "job_category": "backend",
    "timestamp": "2026-05-06T10:30:00Z"
  },
  "errors": []
}
```

### Log Outcome

```
POST /api/v1/abc/outcomes
```

**Request body:**

```json
{
  "behavior_event_id": "behavior_456",
  "outcome_type": "interview",
  "response_time_days": 4
}
```

Logging this outcome immediately refreshes the user's strategy profile. Future backend recommendations now score higher for this user.

### Strategy Profile

```
GET /api/v1/abc/strategy-profile?user_id=user-123
```

**Response:**

```json
{
  "success": true,
  "data": {
    "user_id": "user-123",
    "category_weights": {
      "backend": 0.74,
      "frontend": 0.42,
      "data": 0.5
    },
    "category_success_rates": {
      "backend": 0.28,
      "frontend": 0.05
    },
    "category_profiles": {
      "backend": {
        "applications_count": 18,
        "interviews_count": 5,
        "rejection_count": 2,
        "no_response_count": 3,
        "offers_count": 1,
        "follow_up_count": 1,
        "success_rate": 0.28,
        "avg_response_time": 3.9,
        "click_rate": 0.62,
        "application_rate": 0.48,
        "abandonment_rate": 0.04,
        "resume_performance_score": 0.31,
        "score": 0.66,
        "weight": 0.74,
        "confidence": 0.86
      }
    },
    "updated_at": "2026-05-06T10:31:00Z"
  },
  "errors": []
}
```

### Adaptation Example

Tested behavior:
- New users start with neutral category weights and mostly rank by `base_match_score`.
- Repeated backend applications with interview outcomes increase backend category weight and push backend jobs upward.
- Repeated frontend applications with `no_response` outcomes reduce frontend outcome score and future frontend ranking.
- Two users with opposite histories receive different rankings for the same two jobs.

**Failure response:**

```json
{
  "success": false,
  "data": null,
  "errors": [
    {
      "code": "missing_plan_step",
      "message": "Planner omitted required step 'track'",
      "hunt_id": "5a570e5f-...",
      "step": "plan",
      "retryable": false,
      "details": { "expected_step": "track" }
    }
  ]
}
```

### Fetch a Hunt

```
GET /api/v1/hunts/{hunt_id}
```

Returns the full `HuntResult` for a previously completed or failed hunt.

### Fetch Jobs for a Hunt

```
GET /api/v1/hunts/{hunt_id}/jobs
```

Returns the list of `Job` objects discovered during the search step.

### Fetch Applications for a Hunt

```
GET /api/v1/hunts/{hunt_id}/applications
```

Returns the list of `Application` objects with embedded resume and cover letter.

---

## ⚙️ Configuration

All configuration is loaded from environment variables. Copy `.env.example` to `.env` and customise:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| **LLM** | | |
| `LLM_PROVIDER` | `openai` | LLM provider |
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used for plan/resume/cover letter generation |
| `OPENAI_TEMPERATURE` | `0.4` | Sampling temperature |
| `OPENAI_MAX_TOKENS` | `2048` | Max tokens per LLM call |
| `LLM_TIMEOUT_SECONDS` | `20.0` | Timeout for LLM calls |
| **Application** | | |
| `APP_NAME` | `Autonomous Job Hunt AI Agent` | Application name (shown in docs) |
| `APP_VERSION` | `2.0.0` | Reported in health check |
| `DEBUG` | `false` | Enable debug mode / auto-reload |
| `LOG_LEVEL` | `INFO` | Python log level |
| **Storage** | | |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/job_hunt_agent` | Async database connection string |
| **Job Search** | | |
| `MAX_JOBS_PER_SEARCH` | `10` | Max jobs returned per search |
| `DEFAULT_COUNTRY` | `India` | Default country for job search |
| `REQUEST_TIMEOUT_SECONDS` | `15.0` | HTTP timeout for scraper |
| `STEP_RETRY_ATTEMPTS` | `3` | Retry count for transient step failures |
| `STEP_RETRY_BASE_DELAY_SECONDS` | `0.5` | Base delay for retry backoff |
| `STEP_RETRY_MAX_DELAY_SECONDS` | `4.0` | Max delay for retry backoff |
| `MAX_PARALLEL_JOB_TASKS` | `4` | Concurrent resume/cover letter generation |
| **Behavior** | | |
| `BEHAVIOR_MIN_APPLICATIONS` | `5` | Minimum application count before classification |
| `BEHAVIOR_ANALYSIS_WINDOW_DAYS` | `30` | Window used for behavior metrics |
| **Rate Limit** | | |
| `HUNT_RATE_LIMIT_REQUESTS` | `10` | Max hunt requests per client window |
| `HUNT_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window length |
| **API Server** | | |
| `API_PREFIX` | `/api/v1` | URL prefix for all routes |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| **CORS** | | |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `CORS_ALLOW_CREDENTIALS` | `true` | Allow credentials (rejected if origins = `*`) |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **PostgreSQL** (production) — or use SQLite for local testing
- **OpenAI API key**

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd <project-dir>

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY and DATABASE_URL
```

### Running the Server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Or using the built-in entrypoint:

```bash
python -m backend.main
```

The API will be available at `http://localhost:8000` with interactive docs at `/docs`.

### Using SQLite for Local Development

If you don't have PostgreSQL available, set:

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./job_hunt_agent.db
```

---

## 🧪 Tests

The test suite uses **isolated SQLite databases** through the same async SQLAlchemy repository layer, so no external infrastructure is required.

```bash
python -m unittest discover -s tests
```

### Test Coverage

| Area | What's Tested |
|---|---|
| **Plan Validation** | Rejects missing, duplicate, and out-of-order steps |
| **API — Input** | Returns `400` for invalid input and invalid plans |
| **API — Failures** | Returns `500` for step execution failures |
| **Concurrency** | Concurrent hunt requests keep jobs and applications isolated by `hunt_id` |
| **Behavior Engine** | Metrics, classification thresholds, behavior endpoints, and adaptive hunt volume |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| ORM | [SQLAlchemy 2.0+](https://www.sqlalchemy.org/) (async) |
| Database (prod) | PostgreSQL via [asyncpg](https://github.com/MagicStack/asyncpg) |
| Database (test) | SQLite via [aiosqlite](https://github.com/omnilib/aiosqlite) |
| LLM Client | [OpenAI Python SDK](https://github.com/openai/openai-python) |
| Validation | [Pydantic v2](https://docs.pydantic.dev/) |
| HTTP Client | [httpx](https://www.python-httpx.org/) |
| HTML Parsing | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| Logging | Structured JSON via stdlib `logging` |

---

## 📜 License

This project is for educational and personal use.
