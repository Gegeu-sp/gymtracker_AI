<!--
SYNC IMPACT REPORT
Version change: Template -> v1.0.0
Modified principles: Initialized GymTracker AI core principles
Added sections: Core Principles (I. Modular FastAPI Architecture, II. AI & OCR Resilience, III. Database Integrity, IV. Test-Driven Quality & Verification, V. API Contracts & REST Standards), Governance
Templates requiring updates: ✅ .specify/templates/plan-template.md, ✅ .specify/templates/spec-template.md
Follow-up TODOs: None
-->

# GymTracker AI Constitution

## Core Principles

### I. Modular FastAPI Architecture
Features MUST be decoupled into distinct layers:
- **Routers (`app/routers/`)**: Expose RESTful endpoints, handle HTTP requests/responses, and delegate business logic.
- **Services (`app/services/`)**: Implement core business logic, workout calculations, and AI/OCR integrations independently of HTTP details.
- **Models & Schemas (`app/models.py`, `app/schemas.py`)**: Define database persistence tables and Pydantic validation schemas.
- Cross-layer leakage is forbidden; business logic MUST NOT reside directly inside router handlers.

### II. AI & OCR Resilience
Integrations with AI (Groq, OpenAI) and OCR engines (EasyOCR):
- MUST implement graceful error handling and fallbacks for network latency or API failures.
- MUST validate all structured outputs from LLMs using Pydantic schemas prior to database persistence.
- MUST keep prompt templates and AI service configurations decoupled in `app/services/`.

### III. Database Integrity & Data Security
Database interactions via SQLAlchemy:
- MUST utilize explicit transaction boundaries and session lifecycle management.
- MUST enforce data validation via Pydantic schemas at system boundaries to prevent invalid data injection.
- Database schema changes MUST be tracked and repeatable.

### IV. Test-Driven Quality & Verification
Quality and stability controls:
- Code changes or new features MUST include automated tests using `pytest` and `httpx`.
- Endpoints MUST be tested for both success (2xx) and error handling (4xx/5xx) scenarios.
- Pull requests and code edits MUST pass test suites before merging or deployment.

### V. API Contracts & REST Standards
API design principles:
- Endpoints MUST adhere to standard HTTP verbs (GET, POST, PUT, DELETE) and status codes.
- Response payloads MUST return structured JSON conforming to explicit Pydantic response schemas.
- Interactive documentation (Swagger/OpenAPI) MUST accurately reflect all available routes and parameters.

## Development Workflow & Quality Gates
- All feature additions MUST start with a specification and implementation plan under `.specify/`.
- Code changes MUST preserve documentation and existing function signatures unless explicit migration is planned.
- Dependencies MUST remain declared in `requirements.txt` with compatible version bounds.

## Governance
- This Constitution supersedes informal practices and establishes binding technical guidelines for GymTracker AI.
- Amendments to these principles require documenting the rationale, updating version numbers semantically, and propagating changes to `.specify/`.
- **Version bump policy**:
  - **MAJOR**: Structural shifts in architecture or breaking governance changes.
  - **MINOR**: Addition of new core principles or major technical guidelines.
  - **PATCH**: Refinements, clarifications, or minor documentation fixes.

**Version**: 1.0.0 | **Ratified**: 2026-07-24 | **Last Amended**: 2026-07-24
